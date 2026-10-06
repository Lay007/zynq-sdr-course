`timescale 1ns/1ps
// Time-domain carrier frequency offset (CFO) correction for the Block 8 OFDM RX.
//
// Sits in front of ofdm_cp16_remover on the 80-sample CP16 symbol stream and
// corrects every symbol with an estimate that already includes it, so even
// the first (training) symbol is corrected:
//
//   FILL : the 80 samples are written into a symbol buffer; meanwhile the CP
//          correlation P_sym = sum_{n<16} x[n] * conj(x[n+64]) is formed. For
//          an offset eps (cycles/sample) its angle is -2*pi*64*eps.
//   ANGLE: P_acc += P_sym (accumulated since reset or `restart`), shifted down
//          until max(|re|,|im|) < 2^22, then a 20-step vectoring CORDIC gives
//          theta = angle(P_acc) with 2*pi = 2^24.
//   DRAIN: the buffered samples leave through a pipelined 16-step rotation
//          CORDIC. A 32-bit NCO phase (2*pi = 2^32) advances by theta * 4 =
//          theta/64 per sample, runs across symbols, and each sample is
//          rotated by phase >> 8: x * exp(j*theta*k/64) = x * exp(-j*2*pi*eps*k).
//          The CORDIC gain is removed with 19898/2^15 and the result is rounded
//          (half away from zero) and saturated to Q1.15.
//
// A constant phase is left over; the pilot phase tracker removes it. The CP
// correlation is unambiguous while |eps| < 1/128 cycles/sample (half a
// subcarrier spacing). tools/ofdm_cfo_corrector_fixed.py models the block bit
// for bit.
//
// Throughput: the input stalls while a symbol drains (about 2 x 80 clocks per
// 80 samples plus ~25 for the angle). The output pipeline (19 clocks) stalls
// as a whole under backpressure. frame_error is set (sticky) when in_last does
// not mark the 80th sample.
module ofdm_cfo_corrector (
    input  wire                clk,
    input  wire                resetn,
    input  wire                restart,     // forget the accumulated estimate and the phase

    input  wire                in_valid,
    output wire                in_ready,
    input  wire signed [15:0]  in_re,
    input  wire signed [15:0]  in_im,
    input  wire                in_last,

    output wire                out_valid,
    input  wire                out_ready,
    output wire signed [15:0]  out_re,
    output wire signed [15:0]  out_im,
    output wire                out_last,

    output reg signed [23:0]   theta,       // angle(P_acc), 2*pi = 2^24
    output reg [15:0]          symbol_count,
    output reg                 frame_error
);

    localparam integer XW = 21;              // rotation datapath width
    localparam integer ROT = 16;
    localparam integer VEC = 20;
    localparam signed [23:0] HALF_PI = 24'sd4194304;
    localparam signed [15:0] KINV = 16'sd19898;

    function automatic signed [23:0] atan_const;
        input integer i;
        begin
            case (i)
                0:  atan_const = 24'sd2097152;
                1:  atan_const = 24'sd1238021;
                2:  atan_const = 24'sd654136;
                3:  atan_const = 24'sd332050;
                4:  atan_const = 24'sd166669;
                5:  atan_const = 24'sd83416;
                6:  atan_const = 24'sd41718;
                7:  atan_const = 24'sd20860;
                8:  atan_const = 24'sd10430;
                9:  atan_const = 24'sd5215;
                10: atan_const = 24'sd2608;
                11: atan_const = 24'sd1304;
                12: atan_const = 24'sd652;
                13: atan_const = 24'sd326;
                14: atan_const = 24'sd163;
                15: atan_const = 24'sd81;
                16: atan_const = 24'sd41;
                17: atan_const = 24'sd20;
                18: atan_const = 24'sd10;
                default: atan_const = 24'sd5;
            endcase
        end
    endfunction

    function automatic signed [15:0] round_sat17;
        input signed [37:0] value;   // round(value / 2^17), saturated
        reg signed [37:0] r;
        begin
            if (value >= 0)
                r = (value + 38'sd65536) >>> 17;
            else
                r = -(((-value) + 38'sd65536) >>> 17);
            if (r > 38'sd32767)
                round_sat17 = 16'sh7fff;
            else if (r < -38'sd32768)
                round_sat17 = 16'sh8000;
            else
                round_sat17 = r[15:0];
        end
    endfunction

    function [5:0] top_bit48;     // index of the highest set bit of a 48-bit value
        input [47:0] value;
        integer b;
        begin
            top_bit48 = 6'd0;
            for (b = 0; b < 48; b = b + 1)
                if (value[b])
                    top_bit48 = b[5:0];
        end
    endfunction

    localparam [2:0] S_FILL = 3'd0, S_FLUSH = 3'd1, S_ACC = 3'd2, S_NORM = 3'd3,
                     S_SHIFT = 3'd4, S_ITER = 3'd5, S_DRAIN = 3'd6;

    reg [2:0] state;
    reg [6:0] wr_count;
    reg [6:0] rd_count;
    reg [1:0] flush_count;

    reg [31:0] buffer [0:79];
    integer init_k;
    initial
        for (init_k = 0; init_k < 80; init_k = init_k + 1)
            buffer[init_k] = 32'd0;

    // ---- CP correlation (two-stage pipelined multiply-accumulate) ----
    reg               c_valid;
    reg signed [15:0] c_ar, c_ai, c_br, c_bi;
    reg               m_valid;
    reg signed [31:0] m_rr, m_ii, m_ir, m_ri;
    reg signed [37:0] p_sym_re, p_sym_im;
    reg signed [47:0] acc_re, acc_im;

    wire accept = in_valid && in_ready;
    wire [31:0] cp_word = buffer[wr_count - 7'd64];

    // ---- vectoring CORDIC (sequential) ----
    reg [5:0]         n_shift;
    reg               n_zero;
    reg signed [25:0] v_x, v_y;
    reg signed [23:0] v_z;
    reg [4:0]         v_i;
    wire [47:0] abs_re = acc_re[47] ? -acc_re : acc_re;
    wire [47:0] abs_im = acc_im[47] ? -acc_im : acc_im;
    wire [47:0] abs_max = (abs_re > abs_im) ? abs_re : abs_im;
    wire signed [47:0] sh_re = acc_re >>> n_shift;
    wire signed [47:0] sh_im = acc_im >>> n_shift;
    wire signed [23:0] v_z_next = (v_y >= 0) ? v_z + atan_const(v_i) : v_z - atan_const(v_i);

    // ---- NCO ----
    reg [31:0] phase;
    reg [31:0] delta;

    // ---- rotation pipeline: stage 0 pre-rotation, 1..16 iterations,
    //      17 gain products, 18 rounding (output registers) ----
    reg               r_valid [0:ROT+1];
    reg               r_last  [0:ROT+1];
    reg signed [XW-1:0] r_x [0:ROT];
    reg signed [XW-1:0] r_y [0:ROT];
    reg signed [23:0]   r_a [0:ROT];
    reg signed [37:0]   g_x, g_y;
    reg               o_valid;
    reg               o_last;
    reg signed [15:0] o_re, o_im;

    wire en = !o_valid || out_ready;                 // the whole pipeline moves together
    wire issue = (state == S_DRAIN) && en;
    wire [31:0] rd_word = buffer[rd_count];
    wire signed [XW-1:0] in_x = {{(XW-18){rd_word[31]}}, rd_word[31:16], 2'b00};
    wire signed [XW-1:0] in_y = {{(XW-18){rd_word[15]}}, rd_word[15:0], 2'b00};
    wire signed [23:0] in_a = phase[31:8];

    assign in_ready = resetn && (state == S_FILL);
    assign out_valid = o_valid;
    assign out_re = o_re;
    assign out_im = o_im;
    assign out_last = o_last;

    integer k;

    always @(posedge clk) begin
        if (!resetn) begin
            state <= S_FILL;
            wr_count <= 7'd0;
            rd_count <= 7'd0;
            flush_count <= 2'd0;
            c_valid <= 1'b0;
            m_valid <= 1'b0;
            p_sym_re <= 38'sd0;
            p_sym_im <= 38'sd0;
            acc_re <= 48'sd0;
            acc_im <= 48'sd0;
            phase <= 32'd0;
            delta <= 32'd0;
            theta <= 24'sd0;
            symbol_count <= 16'd0;
            frame_error <= 1'b0;
            o_valid <= 1'b0;
            o_last <= 1'b0;
            o_re <= 16'sd0;
            o_im <= 16'sd0;
            for (k = 0; k <= ROT + 1; k = k + 1) begin
                r_valid[k] <= 1'b0;
                r_last[k] <= 1'b0;
            end
        end else begin
            // CP correlation pipeline.
            c_valid <= accept && (wr_count >= 7'd64);
            c_ar <= $signed(cp_word[31:16]);
            c_ai <= $signed(cp_word[15:0]);
            c_br <= in_re;
            c_bi <= in_im;
            m_valid <= c_valid;
            m_rr <= c_ar * c_br;
            m_ii <= c_ai * c_bi;
            m_ir <= c_ai * c_br;
            m_ri <= c_ar * c_bi;
            if (m_valid) begin
                p_sym_re <= p_sym_re + m_rr + m_ii;
                p_sym_im <= p_sym_im + m_ir - m_ri;
            end

            case (state)
                S_FILL: begin
                    if (accept) begin
                        buffer[wr_count] <= {in_re, in_im};
                        if (in_last != (wr_count == 7'd79))
                            frame_error <= 1'b1;
                        if (wr_count == 7'd79) begin
                            wr_count <= 7'd0;
                            flush_count <= 2'd0;
                            state <= S_FLUSH;
                        end else begin
                            wr_count <= wr_count + 7'd1;
                        end
                    end
                end
                S_FLUSH: begin
                    // let the last products reach p_sym
                    flush_count <= flush_count + 2'd1;
                    if (flush_count == 2'd2)
                        state <= S_ACC;
                end
                S_ACC: begin
                    acc_re <= acc_re + p_sym_re;
                    acc_im <= acc_im + p_sym_im;
                    p_sym_re <= 38'sd0;
                    p_sym_im <= 38'sd0;
                    state <= S_NORM;
                end
                S_NORM: begin
                    n_zero <= (abs_max == 48'd0);
                    n_shift <= (top_bit48(abs_max) >= 6'd22) ? (top_bit48(abs_max) - 6'd21) : 6'd0;
                    state <= S_SHIFT;
                end
                S_SHIFT: begin
                    // x, y now fit 23 bits; pre-rotate into the right half-plane.
                    if (sh_re[47]) begin
                        if (!sh_im[47]) begin
                            v_x <= sh_im[25:0];
                            v_y <= -sh_re[25:0];
                            v_z <= HALF_PI;
                        end else begin
                            v_x <= -sh_im[25:0];
                            v_y <= sh_re[25:0];
                            v_z <= -HALF_PI;
                        end
                    end else begin
                        v_x <= sh_re[25:0];
                        v_y <= sh_im[25:0];
                        v_z <= 24'sd0;
                    end
                    v_i <= 5'd0;
                    state <= S_ITER;
                end
                S_ITER: begin
                    if (v_y >= 0) begin
                        v_x <= v_x + (v_y >>> v_i);
                        v_y <= v_y - (v_x >>> v_i);
                        v_z <= v_z + atan_const(v_i);
                    end else begin
                        v_x <= v_x - (v_y >>> v_i);
                        v_y <= v_y + (v_x >>> v_i);
                        v_z <= v_z - atan_const(v_i);
                    end
                    v_i <= v_i + 5'd1;
                    if (v_i == VEC - 1) begin
                        state <= S_DRAIN;
                        rd_count <= 7'd0;
                        symbol_count <= symbol_count + 16'd1;
                    end
                end
                S_DRAIN: begin
                    if (issue) begin
                        phase <= phase + delta;
                        if (rd_count == 7'd79) begin
                            rd_count <= 7'd0;
                            state <= S_FILL;
                        end else begin
                            rd_count <= rd_count + 7'd1;
                        end
                    end
                end
                default: state <= S_FILL;
            endcase

            // theta and the NCO step take effect for the symbol being drained.
            if (state == S_ITER && v_i == VEC - 1) begin
                theta <= n_zero ? 24'sd0 : v_z_next;
                delta <= n_zero ? 32'd0 : ({{8{v_z_next[23]}}, v_z_next} << 2);
            end

            if (restart) begin
                acc_re <= 48'sd0;
                acc_im <= 48'sd0;
                phase <= 32'd0;
            end

            // Rotation pipeline.
            if (en) begin
                r_valid[0] <= issue;
                r_last[0] <= (rd_count == 7'd79);
                r_a[0] <= in_a;
                if (in_a > HALF_PI) begin
                    r_x[0] <= -in_y;
                    r_y[0] <= in_x;
                    r_a[0] <= in_a - HALF_PI;
                end else if (in_a < -HALF_PI) begin
                    r_x[0] <= in_y;
                    r_y[0] <= -in_x;
                    r_a[0] <= in_a + HALF_PI;
                end else begin
                    r_x[0] <= in_x;
                    r_y[0] <= in_y;
                end
                for (k = 0; k < ROT; k = k + 1) begin
                    r_valid[k + 1] <= r_valid[k];
                    r_last[k + 1] <= r_last[k];
                    if (r_a[k] >= 0) begin
                        r_x[k + 1] <= r_x[k] - (r_y[k] >>> k);
                        r_y[k + 1] <= r_y[k] + (r_x[k] >>> k);
                        r_a[k + 1] <= r_a[k] - atan_const(k);
                    end else begin
                        r_x[k + 1] <= r_x[k] + (r_y[k] >>> k);
                        r_y[k + 1] <= r_y[k] - (r_x[k] >>> k);
                        r_a[k + 1] <= r_a[k] + atan_const(k);
                    end
                end
                r_valid[ROT + 1] <= r_valid[ROT];
                r_last[ROT + 1] <= r_last[ROT];
                g_x <= r_x[ROT] * KINV;
                g_y <= r_y[ROT] * KINV;
                o_valid <= r_valid[ROT + 1];
                o_last <= r_last[ROT + 1];
                if (r_valid[ROT + 1]) begin
                    o_re <= round_sat17(g_x);
                    o_im <= round_sat17(g_y);
                end
            end
        end
    end

endmodule
