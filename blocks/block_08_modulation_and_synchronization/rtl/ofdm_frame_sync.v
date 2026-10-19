`timescale 1ns/1ps

// Issue #48, stage 4b: find an OFDM frame in a continuous sample stream and hand the modem its
// symbols, 80 samples each with `last` on the 80th, as ofdm_axi_modem's receiver expects.
//
// The frame starts with a Schmidl & Cox preamble (CP + a 64-sample body of two equal halves, see
// tools/ofdm_rf_link.py). Bit-exact model: tools/ofdm_frame_sync_fixed.py.
//
//   x       = DC-tracked input >> 4 (12 bits, as from the AD9361): m += (x - m) >> 8, x - m
//   p[n]    = conj(x[n-32]) * x[n],     P = sum of the last 32 p
//   e[n]    = |x[n]|^2,                  E = sum of the last 64 e,  R = E >> 1
//   above   = R > E_MIN  and  4 * |P >> SHIFT|^2 > 3 * (R >> SHIFT)^2         (M > 0.75)
//
// A run of `above` of at least MIN_RUN samples is the preamble's plateau; when it ends, its centre
// c (window start index) gives the first symbol after the preamble at c + 8 + 64 - BACKOFF. The
// input is delayed by DELAY samples, so that symbol is still ahead when the plateau has ended, and
// from there FRAME_SYMBOLS * 80 delayed samples go out. The output is the input itself, delayed,
// without the DC tracking (the modem's subcarrier 0 is unused). The input has no back-pressure (a
// converter at a few MS/s); the output goes through a FIFO_DEPTH-sample FIFO with `out_ready`,
// because the modem's receiver is not ready for about 107 clocks after every symbol (its sequential
// FFT): at 2.083 MS/s and 100 MHz (48 clocks per sample) that cost 2 samples per symbol without the
// FIFO. On average the receiver needs between 9 and 12 clocks per sample (in simulation 8 overflowed
// this FIFO, 12 did not), so the board's 48 leave a wide margin. Samples that find the FIFO full are
// counted in `overflows`. A plateau that ends while a frame is going out is ignored and counted.
//
// Pipeline. Written as one clock per sample, the metric was 34 logic levels deep (Vivado: -16 ns at
// 100 MHz). Here every recurrence (the DC tracker, the rings, the running sums) is one stage, and
// the products and squares get registers of their own, so the metric decision for a sample comes
// LATENCY clocks after it. The output side works on the input sample at once and reads the decision
// registers; the first symbol lies more than DELAY - 70 samples ahead when they change, so the
// latency does not move the output. With samples at least LATENCY + 1 clocks apart (12 and more: CI
// and the board) the block behaves exactly as the model, frames_missed included. The rings are not
// reset (so that they map to distributed RAM); until they have been filled once their reads count
// as 0, which is what the model's sums over a not yet full window do.
module ofdm_frame_sync #(
    parameter integer E_MIN = 2000,
    parameter integer SHIFT = 8,
    parameter integer MIN_RUN = 8,
    parameter integer BACKOFF = 4,
    parameter integer DELAY = 128,       // power of two, > the decision latency (~70 samples)
    parameter integer FIFO_DEPTH = 16    // power of two
) (
    input  wire               clk,
    input  wire               rst,
    input  wire [7:0]         frame_symbols,     // symbols per frame after the preamble (training + data)
    input  wire               in_valid,
    input  wire signed [15:0] in_re,
    input  wire signed [15:0] in_im,
    output wire               out_valid,
    input  wire               out_ready,
    output wire signed [15:0] out_re,
    output wire signed [15:0] out_im,
    output wire               out_last,
    output wire               frame_start,       // with the first sample of a frame
    output reg  [15:0]        frames_found,
    output reg  [15:0]        frames_missed,     // plateaus that ended while a frame was going out
    output reg  [15:0]        overflows          // samples lost because the output FIFO was full
);

localparam integer H = 32, N = 64, CP = 16;
localparam integer DA = $clog2(DELAY);
// Widths. |x| <= 4096 after the DC tracker (13 bits); |p|, e < 2^25; |P| < 2^30, E < 2^31.
localparam integer XW = 14, PW = 27, SW = 33;
localparam integer QW = SW - 1 - SHIFT;             // P >> SHIFT and R >> SHIFT (< 2^(30-SHIFT)), signed
localparam integer LATENCY = 10;                    // clocks from in_valid to the decision

// ---------------------------------------------------------------------------------------------
// Stage 1: DC tracker, 12-bit samples
// ---------------------------------------------------------------------------------------------
reg signed [27:0] m_re = 0, m_im = 0;              // DC estimate, 8 fraction bits
wire signed [11:0] s_re = in_re >>> 4;
wire signed [11:0] s_im = in_im >>> 4;
wire signed [27:0] y_re = ($signed({{16{s_re[11]}}, s_re}) <<< 8) - m_re;
wire signed [27:0] y_im = ($signed({{16{s_im[11]}}, s_im}) <<< 8) - m_im;

reg [31:0] n = 0;                                   // index of the current input sample
reg               v1 = 1'b0;
reg [31:0]        n1 = 0;
reg signed [XW-1:0] x1_re = 0, x1_im = 0;

always @(posedge clk) begin
    v1 <= 1'b0;
    if (rst) begin
        m_re <= 0; m_im <= 0;
    end else if (in_valid) begin
        m_re <= m_re + (y_re >>> 8);
        m_im <= m_im + (y_im >>> 8);
        x1_re <= y_re >>> 8;
        x1_im <= y_im >>> 8;
        n1 <= n;
        v1 <= 1'b1;
    end
end

// ---------------------------------------------------------------------------------------------
// Stage 2: x[n-32] from the ring
// ---------------------------------------------------------------------------------------------
reg signed [XW-1:0] xr_ring [0:H-1];
reg signed [XW-1:0] xi_ring [0:H-1];
reg [4:0] a32 = 0;
reg               v2 = 1'b0;
reg [31:0]        n2 = 0;
reg signed [XW-1:0] x2_re = 0, x2_im = 0, xo2_re = 0, xo2_im = 0;

always @(posedge clk) begin
    v2 <= 1'b0;
    if (rst) begin
        a32 <= 0;
    end else if (v1) begin
        xr_ring[a32] <= x1_re;
        xi_ring[a32] <= x1_im;
        xo2_re <= (n1 >= H) ? xr_ring[a32] : {XW{1'b0}};
        xo2_im <= (n1 >= H) ? xi_ring[a32] : {XW{1'b0}};
        x2_re <= x1_re;
        x2_im <= x1_im;
        a32 <= a32 + 1'b1;
        n2 <= n1;
        v2 <= 1'b1;
    end
end

// ---------------------------------------------------------------------------------------------
// Stages 3-4: products, then p and e
// ---------------------------------------------------------------------------------------------
reg               v3 = 1'b0, v4 = 1'b0;
reg [31:0]        n3 = 0, n4 = 0;
reg signed [2*XW-1:0] m_rr = 0, m_ii = 0, m_ri = 0, m_ir = 0, m_er = 0, m_ei = 0;
reg signed [PW-1:0] p4_re = 0, p4_im = 0, e4 = 0;

always @(posedge clk) begin
    v3 <= v2;
    v4 <= v3;
    n3 <= n2;
    n4 <= n3;
    m_rr <= xo2_re * x2_re;
    m_ii <= xo2_im * x2_im;
    m_ri <= xo2_re * x2_im;
    m_ir <= xo2_im * x2_re;
    m_er <= x2_re * x2_re;
    m_ei <= x2_im * x2_im;
    p4_re <= m_rr + m_ii;
    p4_im <= m_ri - m_ir;
    e4 <= m_er + m_ei;
end

// ---------------------------------------------------------------------------------------------
// Stage 5: running sums over the rings of p (32) and e (64)
// ---------------------------------------------------------------------------------------------
reg signed [PW-1:0] pr_ring [0:H-1];
reg signed [PW-1:0] pi_ring [0:H-1];
reg signed [PW-1:0] e_ring  [0:N-1];
reg [4:0] b32 = 0;
reg [5:0] b64 = 0;
reg signed [SW-1:0] P_re = 0, P_im = 0, E = 0;
reg               v5 = 1'b0;
reg [31:0]        n5 = 0;
wire signed [PW-1:0] po_re = (n4 >= H) ? pr_ring[b32] : {PW{1'b0}};
wire signed [PW-1:0] po_im = (n4 >= H) ? pi_ring[b32] : {PW{1'b0}};
wire signed [PW-1:0] eo    = (n4 >= N) ? e_ring[b64]  : {PW{1'b0}};

always @(posedge clk) begin
    v5 <= 1'b0;
    if (rst) begin
        b32 <= 0; b64 <= 0; P_re <= 0; P_im <= 0; E <= 0;
    end else if (v4) begin
        pr_ring[b32] <= p4_re;
        pi_ring[b32] <= p4_im;
        e_ring[b64]  <= e4;
        P_re <= P_re + p4_re - po_re;
        P_im <= P_im + p4_im - po_im;
        E    <= E + e4 - eo;
        b32 <= b32 + 1'b1;
        b64 <= b64 + 1'b1;
        n5 <= n4;
        v5 <= 1'b1;
    end
end

// ---------------------------------------------------------------------------------------------
// Stages 6-10: shifts, squares (DSP pipeline), the comparison
// ---------------------------------------------------------------------------------------------
reg               v6 = 1'b0, v7 = 1'b0, v8 = 1'b0, v9 = 1'b0, v10 = 1'b0;
reg [31:0]        n6 = 0, n7 = 0, n8 = 0, n9 = 0, n10 = 0;
reg signed [QW-1:0] q_re = 0, q_im = 0, q_r = 0;
reg               big6 = 1'b0, big7 = 1'b0, big8 = 1'b0, big9 = 1'b0;
reg signed [2*QW-1:0] sq7_re = 0, sq7_im = 0, sq7_r = 0, sq8_re = 0, sq8_im = 0, sq8_r = 0;
reg        [2*QW+1:0] lhs9 = 0, rhs9 = 0;
reg               above10 = 1'b0;

always @(posedge clk) begin
    {v6, v7, v8, v9, v10} <= {v5, v6, v7, v8, v9};
    {n6, n7, n8, n9, n10} <= {n5, n6, n7, n8, n9};
    q_re <= P_re >>> SHIFT;
    q_im <= P_im >>> SHIFT;
    q_r  <= (E >>> 1) >>> SHIFT;
    big6 <= (E >>> 1) > E_MIN;
    sq7_re <= q_re * q_re;
    sq7_im <= q_im * q_im;
    sq7_r  <= q_r * q_r;
    big7 <= big6;
    sq8_re <= sq7_re;
    sq8_im <= sq7_im;
    sq8_r  <= sq7_r;
    big8 <= big7;
    lhs9 <= ({2'b00, sq8_re} + {2'b00, sq8_im}) << 2;
    rhs9 <= {2'b00, sq8_r} + ({2'b00, sq8_r} << 1);
    big9 <= big8;
    above10 <= big9 && (lhs9 > rhs9);
end

// ---------------------------------------------------------------------------------------------
// Plateau, decision (stage 11), delayed output (on the input sample)
// ---------------------------------------------------------------------------------------------
reg        in_run = 1'b0;
reg [31:0] run_start = 0, run_last = 0;
reg        active = 1'b0;
reg [31:0] first = 0;
reg [15:0] count = 0, total = 0;
reg [6:0]  pos = 0;
reg signed [15:0] dl_re [0:DELAY-1];
reg signed [15:0] dl_im [0:DELAY-1];
wire [31:0] d = n10 - (N - 1);                      // window start of the metric value now decided
wire [31:0] k = n - DELAY;                          // index of the delayed sample read now
wire [31:0] run_c = (run_start + run_last) >> 1;

integer i;
initial begin
    for (i = 0; i < H; i = i + 1) begin
        xr_ring[i] = 0; xi_ring[i] = 0; pr_ring[i] = 0; pi_ring[i] = 0;
    end
    for (i = 0; i < N; i = i + 1) e_ring[i] = 0;
    for (i = 0; i < DELAY; i = i + 1) begin dl_re[i] = 0; dl_im[i] = 0; end
end

// Output FIFO: {frame_start, last, im, re}
localparam integer FA = $clog2(FIFO_DEPTH);
reg [33:0] fifo [0:FIFO_DEPTH-1];
reg [FA:0] wr_ptr = 0, rd_ptr = 0;
wire       fifo_empty = (wr_ptr == rd_ptr);
wire       fifo_full  = (wr_ptr[FA-1:0] == rd_ptr[FA-1:0]) && (wr_ptr[FA] != rd_ptr[FA]);
assign out_valid   = !fifo_empty;
assign {frame_start, out_last, out_im, out_re} = fifo[rd_ptr[FA-1:0]];
reg        push = 1'b0;
reg [33:0] push_word = 0;

always @(posedge clk) begin
    if (rst) begin
        rd_ptr <= 0;
        wr_ptr <= 0;
        overflows <= 0;
    end else begin
        if (out_valid && out_ready)
            rd_ptr <= rd_ptr + 1'b1;
        if (push) begin
            if (fifo_full) begin
                overflows <= overflows + 1'b1;
            end else begin
                fifo[wr_ptr[FA-1:0]] <= push_word;
                wr_ptr <= wr_ptr + 1'b1;
            end
        end
    end
end

always @(posedge clk) begin
    push <= 1'b0;
    if (rst) begin
        n <= 0; in_run <= 1'b0; active <= 1'b0; frames_found <= 0; frames_missed <= 0;
    end else begin
        // plateau of the metric
        if (v10) begin
            if (above10) begin
                if (!in_run) begin
                    in_run <= 1'b1;
                    run_start <= d;
                end
                run_last <= d;
            end else if (in_run) begin
                in_run <= 1'b0;
                if (run_last - run_start + 1 >= MIN_RUN) begin
                    if (active) begin
                        frames_missed <= frames_missed + 1'b1;
                    end else begin
                        active <= 1'b1;
                        first <= run_c + CP / 2 + N - BACKOFF;
                        count <= 0;
                        total <= frame_symbols * 80;
                        pos <= 0;
                        frames_found <= frames_found + 1'b1;
                    end
                end
            end
        end
        // delayed output: sample k, read before this sample overwrites its slot
        if (in_valid) begin
            dl_re[n[DA-1:0]] <= in_re;
            dl_im[n[DA-1:0]] <= in_im;
            if (active && n >= DELAY && k >= first) begin
                push <= 1'b1;
                push_word <= {(count == 0), (pos == 7'd79), dl_im[n[DA-1:0]], dl_re[n[DA-1:0]]};
                pos <= (pos == 7'd79) ? 7'd0 : pos + 1'b1;
                count <= count + 1'b1;
                if (count + 1'b1 == total)
                    active <= 1'b0;
            end
            n <= n + 1'b1;
        end
    end
end

endmodule
