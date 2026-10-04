`timescale 1ns/1ps
// Per-subcarrier channel estimation and equalization for the Block 8 OFDM RX.
//
// Sits between ofdm_fft64_sequential and ofdm_subcarrier_extractor and works on
// the natural-order 64-bin stream:
//
//   TRAIN: the first symbol after reset (or after `retrain`) is a known
//          training symbol: its 48 data carriers carry the fixed bit pattern
//          train_bits() and its four pilots the usual pilot values. For every
//          used bin k the block stores
//              G[k] = Y[k] * conj(sign(X[k]))
//          (only additions: the reference signs are +-1), which is H[k] up to
//          a real factor (sqrt(2) on data carriers, 1 on pilots). Nothing is
//          output for the training symbol.
//   DATA:  every following symbol leaves as
//     NORMALIZE = 0:  Z[k] = Y[k] * conj(G[k]) >> SHIFT          (rounded, saturated)
//          = |H[k]|^2 * X[k] * scale: the channel phase is removed on every
//          carrier, so QPSK hard decisions (signs) are right without a
//          division. The amplitude is NOT normalized: carriers in a fade come
//          out small. Enough for QPSK, not for 16-QAM or for EVM.
//     NORMALIZE = 1:  Z[k] = 2^14 * Y[k] * conj(G[k]) / |G[k]|^2 = 2^14 * Y[k] / G[k]
//          (zero-forcing). After the training symbol the input is stalled while
//          a sequential linear-mode CORDIC computes 1/|G[k]|^2 for every bin:
//          |G|^2 is shifted left by s so that its top bit is bit 35, then 17
//          iterations of  y -/+= x >> i,  z +/-= 2^(16-i)  give z ~ 2^16 * 2^35
//          / (|G|^2 << s). The data path then forms (Y*conj(G)) * z >> (37 - s).
//          With this chain's scaling a data carrier comes out at about +-8192
//          per component whatever |H| is, and a pilot at about +-16384 (its
//          reference is 1.0, not 0.707): every carrier on the same grid, which
//          a 16-QAM slicer needs, with headroom for noise.
//
// Pilots are equalized too, so ofdm_pilot_phase_corrector downstream measures
// only the phase that changed since the training symbol (residual CFO, drift).
//
// Arithmetic: Y Q1.15, G 18-bit signed (Y re/im sums), products 34 bits.
// Both transforms of this chain are scaled by 1/N, so a loopback bin is X/64:
// a QPSK component of 23170 arrives as about 362. SHIFT = 4 then maps a data
// carrier with |H| = 1 to about 16380 per component (half of full scale) and
// saturates only above |H|^2 = 2. Rounding is nearest, half away from zero,
// like the rest of the chain; saturation_count counts clipped components. Null
// and guard bins leave as zero. tools/ofdm_channel_equalizer_fixed.py models
// both modes bit for bit.
//
// Pipeline: registered inputs, registered products, registered output (three
// clocks; NORMALIZE = 1 adds the sum, the 1/|G|^2 product, then splits the
// rounding into magnitude, + half, and shift/saturate: seven clocks), one bin
// per clock; the whole pipeline stalls while the output is
// held. bin_last passes through. `trained` rises when the coefficients are
// ready (after the CORDIC pass when NORMALIZE = 1).
module ofdm_channel_equalizer #(
    parameter integer SHIFT = 4,
    parameter integer NORMALIZE = 0
) (
    input  wire                clk,
    input  wire                resetn,
    input  wire                retrain,

    input  wire                bin_valid,
    output wire                bin_ready,
    input  wire signed [15:0]  bin_re,
    input  wire signed [15:0]  bin_im,
    input  wire [5:0]          bin_index,
    input  wire                bin_last,

    output reg                 out_valid,
    input  wire                out_ready,
    output reg signed [15:0]   out_re,
    output reg signed [15:0]   out_im,
    output reg [5:0]           out_index,
    output reg                 out_last,

    output reg                 trained,
    output reg [15:0]          train_count,
    output reg [31:0]          saturation_count
);

    localparam integer CORDIC_ITERS = 17;

    // Training pattern on the 48 data carriers (index in the allocator's
    // data_k order): {I bit, Q bit}; bit 1 -> negative component, as in the
    // mapper. The same function is in tools/ofdm_channel_equalizer_fixed.py.
    function [1:0] train_bits;
        input [5:0] data_index;
        begin
            train_bits = {data_index[0] ^ data_index[3],
                          data_index[1] ^ data_index[2] ^ data_index[4]};
        end
    endfunction

    // Same mapping as ofdm_subcarrier_allocator.
    function integer data_index_for_bin;
        input [5:0] natural_bin;
        begin
            if ((natural_bin >= 6'd1) && (natural_bin <= 6'd6))
                data_index_for_bin = natural_bin + 23;
            else if ((natural_bin >= 6'd8) && (natural_bin <= 6'd20))
                data_index_for_bin = natural_bin + 22;
            else if ((natural_bin >= 6'd22) && (natural_bin <= 6'd26))
                data_index_for_bin = natural_bin + 21;
            else if ((natural_bin >= 6'd38) && (natural_bin <= 6'd42))
                data_index_for_bin = natural_bin - 38;
            else if ((natural_bin >= 6'd44) && (natural_bin <= 6'd56))
                data_index_for_bin = natural_bin - 39;
            else
                data_index_for_bin = natural_bin - 40;
        end
    endfunction

    // Reference signs of the training symbol: {used, xr_neg, xi_neg, xi_used}.
    function [3:0] train_ref;
        input [5:0] natural_bin;
        reg [1:0] bits;
        begin
            if ((natural_bin == 6'd0) || ((natural_bin >= 6'd27) && (natural_bin <= 6'd37)))
                train_ref = 4'b0000;                       // DC and guard
            else if ((natural_bin == 6'd7) || (natural_bin == 6'd43) || (natural_bin == 6'd57))
                train_ref = 4'b1000;                       // pilot +1
            else if (natural_bin == 6'd21)
                train_ref = 4'b1100;                       // pilot -1
            else begin
                bits = train_bits(data_index_for_bin(natural_bin));
                train_ref = {1'b1, bits[1], bits[0], 1'b1};
            end
        end
    endfunction

    function automatic signed [15:0] round_sat;
        input signed [34:0] value;
        reg signed [34:0] magnitude;
        reg signed [34:0] rounded;
        begin
            if (value >= 0)
                rounded = (value + (35'sd1 <<< (SHIFT - 1))) >>> SHIFT;
            else begin
                magnitude = -value;
                rounded = -((magnitude + (35'sd1 <<< (SHIFT - 1))) >>> SHIFT);
            end
            if (rounded > 35'sd32767)
                round_sat = 16'sh7fff;
            else if (rounded < -35'sd32768)
                round_sat = 16'sh8000;
            else
                round_sat = rounded[15:0];
        end
    endfunction

    function automatic is_sat;
        input signed [34:0] value;
        reg signed [34:0] magnitude;
        reg signed [34:0] rounded;
        begin
            if (value >= 0)
                rounded = (value + (35'sd1 <<< (SHIFT - 1))) >>> SHIFT;
            else begin
                magnitude = -value;
                rounded = -((magnitude + (35'sd1 <<< (SHIFT - 1))) >>> SHIFT);
            end
            is_sat = (rounded > 35'sd32767) || (rounded < -35'sd32768);
        end
    endfunction

    // NORMALIZE = 1: Z = sign * ((|Q| + 2^(sh-1)) >> sh), saturated to Q1.15
    // (round half away from zero, like the rest of the chain). Done over three
    // clocks; these two helpers are the last one. r is the rounded magnitude.
    function automatic r_too_big;           // sign * r outside Q1.15
        input [52:0] r;
        input negative;
        begin
            if (negative)
                r_too_big = (|r[52:16]) || (r[15] && (|r[14:0]));   // r > 32768
            else
                r_too_big = |r[52:15];                              // r > 32767
        end
    endfunction

    function automatic signed [15:0] signed_sat;
        input [52:0] r;
        input negative;
        begin
            if (r_too_big(r, negative))
                signed_sat = negative ? 16'sh8000 : 16'sh7fff;
            else if (negative)
                signed_sat = -$signed({1'b0, r[15:0]});    // r <= 32768 here
            else
                signed_sat = $signed(r[15:0]);             // r <= 32767 here
        end
    endfunction

    reg signed [17:0] g_re [0:63];
    reg signed [17:0] g_im [0:63];
    reg        [16:0] inv_m [0:63];   // NORMALIZE = 1: CORDIC quotient z
    reg        [5:0]  inv_sh [0:63];  // NORMALIZE = 1: output shift 37 - s

    integer init_k;
    initial
        for (init_k = 0; init_k < 64; init_k = init_k + 1) begin
            g_re[init_k] = 18'sd0;
            g_im[init_k] = 18'sd0;
            inv_m[init_k] = 17'd0;
            inv_sh[init_k] = 6'd37;
        end

    // Stage 0: registered input bin and its coefficient.
    reg               s0_valid;
    reg               s0_train;
    reg signed [15:0] s0_re;
    reg signed [15:0] s0_im;
    reg signed [17:0] s0_g_re;
    reg signed [17:0] s0_g_im;
    reg        [16:0] s0_m;
    reg        [5:0]  s0_sh;
    reg [5:0]         s0_index;
    reg               s0_last;
    // Stage 1: products.
    reg               s1_valid;
    reg               s1_train;
    reg signed [33:0] s1_rr;   // Yr*Gr
    reg signed [33:0] s1_ii;   // Yi*Gi
    reg signed [33:0] s1_ir;   // Yi*Gr
    reg signed [33:0] s1_ri;   // Yr*Gi
    reg        [16:0] s1_m;
    reg        [5:0]  s1_sh;
    reg [5:0]         s1_index;
    reg               s1_last;
    // NORMALIZE = 1, stage 2: Y*conj(G); stage 3: times 1/|G|^2.
    reg               s2_valid;
    reg signed [34:0] s2_p_re;
    reg signed [34:0] s2_p_im;
    reg        [16:0] s2_m;
    reg        [5:0]  s2_sh;
    reg [5:0]         s2_index;
    reg               s2_last;
    reg               s3_valid;
    reg signed [52:0] s3_q_re;
    reg signed [52:0] s3_q_im;
    reg        [5:0]  s3_sh;
    reg [5:0]         s3_index;
    reg               s3_last;
    // Stage 4: sign and magnitude; stage 5: magnitude + 2^(sh-1).
    reg               s4_valid;
    reg               s4_neg_re;
    reg               s4_neg_im;
    reg        [52:0] s4_mag_re;
    reg        [52:0] s4_mag_im;
    reg        [5:0]  s4_sh;
    reg [5:0]         s4_index;
    reg               s4_last;
    reg               s5_valid;
    reg               s5_neg_re;
    reg               s5_neg_im;
    reg        [52:0] s5_sum_re;
    reg        [52:0] s5_sum_im;
    reg        [5:0]  s5_sh;
    reg [5:0]         s5_index;
    reg               s5_last;
    reg [1:0]         saturation_pending;

    wire signed [34:0] z_re = {s1_rr[33], s1_rr} + {s1_ii[33], s1_ii};
    wire signed [34:0] z_im = {s1_ir[33], s1_ir} - {s1_ri[33], s1_ri};
    wire [52:0] r_re = s5_sum_re >> s5_sh;
    wire [52:0] r_im = s5_sum_im >> s5_sh;

    // Training estimate G = Y * conj(sign X) from the registered input bin.
    wire [3:0] ref_now = train_ref(s0_index);
    wire signed [17:0] yr = {{2{s0_re[15]}}, s0_re};
    wire signed [17:0] yi = {{2{s0_im[15]}}, s0_im};
    wire signed [17:0] ar = ref_now[2] ? -yr : yr;          // xr * Yr
    wire signed [17:0] ai = ref_now[2] ? -yi : yi;          // xr * Yi
    wire signed [17:0] br = ref_now[1] ? -yr : yr;          // xi * Yr
    wire signed [17:0] bi = ref_now[1] ? -yi : yi;          // xi * Yi
    wire signed [17:0] est_re = !ref_now[3] ? 18'sd0 : (ref_now[0] ? ar + bi : ar);
    wire signed [17:0] est_im = !ref_now[3] ? 18'sd0 : (ref_now[0] ? ai - br : ai);

    // ---- NORMALIZE = 1: sequential CORDIC division 1/|G|^2 per bin ----
    localparam [2:0] N_IDLE = 3'd0, N_LOAD = 3'd1, N_LZ = 3'd2, N_SHIFT = 3'd3, N_ITER = 3'd4, N_STORE = 3'd5;
    reg [2:0]         n_state;
    reg [5:0]         n_bin;
    reg [35:0]        n_e;      // |G|^2
    reg [5:0]         n_s;      // normalizing left shift
    reg signed [37:0] n_y;
    reg signed [18:0] n_z;
    reg [4:0]         n_i;
    reg [35:0]        n_xs;     // x >> i, shifted one place per iteration
    reg [18:0]        n_step;   // 2^(16-i)
    reg               norm_busy;

    wire signed [17:0] n_gr = g_re[n_bin];
    wire signed [17:0] n_gi = g_im[n_bin];

    function [5:0] leading_shift;   // left shift that puts the top 1 at bit 35
        input [35:0] value;
        integer b;
        begin
            leading_shift = 6'd0;
            for (b = 0; b < 36; b = b + 1)
                if (value[b])
                    leading_shift = 6'd35 - b[5:0];
        end
    endfunction

    reg mode_train;   // the symbol now entering is a training symbol
    wire stall = out_valid && !out_ready;
    assign bin_ready = resetn && !stall && !norm_busy;

    always @(posedge clk) begin
        if (!resetn) begin
            mode_train <= 1'b1;
            trained <= 1'b0;
            train_count <= 16'd0;
            saturation_count <= 32'd0;
            s0_valid <= 1'b0;
            s1_valid <= 1'b0;
            s2_valid <= 1'b0;
            s3_valid <= 1'b0;
            s4_valid <= 1'b0;
            s5_valid <= 1'b0;
            saturation_pending <= 2'd0;
            out_valid <= 1'b0;
            out_re <= 16'sd0;
            out_im <= 16'sd0;
            out_index <= 6'd0;
            out_last <= 1'b0;
            s0_train <= 1'b0;
            s1_train <= 1'b0;
            n_state <= N_IDLE;
            n_bin <= 6'd0;
            norm_busy <= 1'b0;
            // The coefficient memories are deliberately not reset: the training
            // symbol (and, with NORMALIZE = 1, the CORDIC pass) writes all 64
            // entries before any data symbol reads them, and a memory without
            // reset can be RAM instead of thousands of flip-flops.
        end else begin
            saturation_count <= saturation_count + saturation_pending;
            saturation_pending <= 2'd0;
            if (retrain)
                mode_train <= 1'b1;

            // CORDIC pass over all 64 bins after a training symbol.
            case (n_state)
                N_LOAD: begin
                    n_e <= n_gr * n_gr + n_gi * n_gi;
                    n_state <= N_LZ;
                end
                N_LZ: begin
                    n_s <= leading_shift(n_e);
                    n_state <= (n_e == 36'd0) ? N_STORE : N_SHIFT;
                end
                N_SHIFT: begin
                    n_xs <= n_e << n_s;
                    n_y <= 38'sd1 <<< 35;
                    n_z <= 19'sd0;
                    n_step <= 19'd65536;
                    n_i <= 5'd0;
                    n_state <= N_ITER;
                end
                N_ITER: begin
                    // Iteration i uses x >> i and 2^(16-i); both registers
                    // shift one place per iteration.
                    if (n_y >= 0) begin
                        n_y <= n_y - $signed({2'b00, n_xs});
                        n_z <= n_z + $signed(n_step);
                    end else begin
                        n_y <= n_y + $signed({2'b00, n_xs});
                        n_z <= n_z - $signed(n_step);
                    end
                    n_xs <= n_xs >> 1;
                    n_step <= n_step >> 1;
                    if (n_i == CORDIC_ITERS - 1)
                        n_state <= N_STORE;
                    n_i <= n_i + 5'd1;
                end
                N_STORE: begin
                    inv_m[n_bin] <= (n_e == 36'd0) ? 17'd0 : n_z[16:0];
                    inv_sh[n_bin] <= (n_e == 36'd0) ? 6'd37 : (6'd37 - n_s);
                    n_bin <= n_bin + 6'd1;
                    if (n_bin == 6'd63) begin
                        n_state <= N_IDLE;
                        norm_busy <= 1'b0;
                        trained <= 1'b1;
                        train_count <= train_count + 16'd1;
                    end else begin
                        n_state <= N_LOAD;
                    end
                end
                default: ;
            endcase

            if (!stall) begin
                // Stage 0.
                s0_valid <= bin_valid && bin_ready;
                if (bin_valid && bin_ready) begin
                    s0_train <= mode_train;
                    s0_re <= bin_re;
                    s0_im <= bin_im;
                    s0_g_re <= g_re[bin_index];
                    s0_g_im <= g_im[bin_index];
                    s0_m <= inv_m[bin_index];
                    s0_sh <= inv_sh[bin_index];
                    s0_index <= bin_index;
                    s0_last <= bin_last;
                    if (bin_last && mode_train && !retrain)
                        mode_train <= 1'b0;
                    // The last training bin: hold the input until 1/|G|^2 is ready.
                    if ((NORMALIZE != 0) && bin_last && mode_train)
                        norm_busy <= 1'b1;
                end

                // Stage 1: store the estimate, or form the products.
                s1_valid <= s0_valid && !s0_train;
                s1_train <= s0_train;
                if (s0_valid && s0_train) begin
                    g_re[s0_index] <= est_re;
                    g_im[s0_index] <= est_im;
                    if (s0_last) begin
                        if (NORMALIZE != 0) begin
                            n_bin <= 6'd0;
                            n_state <= N_LOAD;
                        end else begin
                            trained <= 1'b1;
                            train_count <= train_count + 16'd1;
                        end
                    end
                end
                s1_rr <= s0_re * s0_g_re;
                s1_ii <= s0_im * s0_g_im;
                s1_ir <= s0_im * s0_g_re;
                s1_ri <= s0_re * s0_g_im;
                s1_m <= s0_m;
                s1_sh <= s0_sh;
                s1_index <= s0_index;
                s1_last <= s0_last;

                if (NORMALIZE == 0) begin
                    // Stage 2: output.
                    out_valid <= s1_valid;
                    if (s1_valid) begin
                        out_re <= round_sat(z_re);
                        out_im <= round_sat(z_im);
                        out_index <= s1_index;
                        out_last <= s1_last;
                        saturation_pending <= {1'b0, is_sat(z_re)} + {1'b0, is_sat(z_im)};
                    end
                end else begin
                    // Stage 2: P = Y*conj(G).
                    s2_valid <= s1_valid;
                    s2_p_re <= z_re;
                    s2_p_im <= z_im;
                    s2_m <= s1_m;
                    s2_sh <= s1_sh;
                    s2_index <= s1_index;
                    s2_last <= s1_last;
                    // Stage 3: P * z.
                    s3_valid <= s2_valid;
                    s3_q_re <= s2_p_re * $signed({1'b0, s2_m});
                    s3_q_im <= s2_p_im * $signed({1'b0, s2_m});
                    s3_sh <= s2_sh;
                    s3_index <= s2_index;
                    s3_last <= s2_last;
                    // Stage 4: sign and magnitude.
                    s4_valid <= s3_valid;
                    s4_neg_re <= s3_q_re[52];
                    s4_neg_im <= s3_q_im[52];
                    s4_mag_re <= s3_q_re[52] ? -s3_q_re : s3_q_re;
                    s4_mag_im <= s3_q_im[52] ? -s3_q_im : s3_q_im;
                    s4_sh <= s3_sh;
                    s4_index <= s3_index;
                    s4_last <= s3_last;
                    // Stage 5: + 2^(sh-1).
                    s5_valid <= s4_valid;
                    s5_neg_re <= s4_neg_re;
                    s5_neg_im <= s4_neg_im;
                    s5_sum_re <= s4_mag_re + (53'd1 << (s4_sh - 6'd1));
                    s5_sum_im <= s4_mag_im + (53'd1 << (s4_sh - 6'd1));
                    s5_sh <= s4_sh;
                    s5_index <= s4_index;
                    s5_last <= s4_last;
                    // Stage 6: shift, saturate, apply the sign.
                    out_valid <= s5_valid;
                    if (s5_valid) begin
                        out_re <= signed_sat(r_re, s5_neg_re);
                        out_im <= signed_sat(r_im, s5_neg_im);
                        out_index <= s5_index;
                        out_last <= s5_last;
                        saturation_pending <= {1'b0, r_too_big(r_re, s5_neg_re)} +
                                              {1'b0, r_too_big(r_im, s5_neg_im)};
                    end
                end
            end
        end
    end

endmodule
