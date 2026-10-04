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
//              Z[k] = Y[k] * conj(G[k])  >>> SHIFT   (rounded, saturated)
//          Z[k] = |H[k]|^2 * X[k] * scale: the channel phase is removed on every
//          carrier, so QPSK hard decisions (signs) are right without a
//          division. The amplitude is NOT normalized: carriers in a fade come
//          out small. That is enough for QPSK, not for 16-QAM or for EVM.
//
// Pilots are equalized too, so ofdm_pilot_phase_corrector downstream measures
// only the phase that changed since the training symbol (residual CFO, drift).
//
// Arithmetic: Y Q1.15, G 18-bit signed (Y re/im sums), products 34 bits.
// Both transforms of this chain are scaled by 1/N, so a loopback bin is X/64:
// a QPSK component of 23170 arrives as about 362. SHIFT = 4 then maps a data
// carrier with |H| = 1 to about 16380 per component (half of full scale) and
// saturates only above |H|^2 = 2; a different front-end level needs a
// different SHIFT. Rounding is nearest, half away from
// zero, like the rest of the chain; saturation_count counts clipped components.
// Null and guard bins leave as zero.
//
// Pipeline: registered inputs, registered products, registered output (three
// clocks, one bin per clock); the whole pipeline stalls while the output is
// held. bin_last passes through.
module ofdm_channel_equalizer #(
    parameter integer SHIFT = 4
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

    reg signed [17:0] g_re [0:63];
    reg signed [17:0] g_im [0:63];

    // Stage 0: registered input bin and its coefficient.
    reg               s0_valid;
    reg               s0_train;
    reg signed [15:0] s0_re;
    reg signed [15:0] s0_im;
    reg signed [17:0] s0_g_re;
    reg signed [17:0] s0_g_im;
    reg [5:0]         s0_index;
    reg               s0_last;
    // Stage 1: products.
    reg               s1_valid;
    reg               s1_train;
    reg signed [33:0] s1_rr;   // Yr*Gr
    reg signed [33:0] s1_ii;   // Yi*Gi
    reg signed [33:0] s1_ir;   // Yi*Gr
    reg signed [33:0] s1_ri;   // Yr*Gi
    reg [5:0]         s1_index;
    reg               s1_last;
    reg [1:0]         saturation_pending;

    wire signed [34:0] z_re = {s1_rr[33], s1_rr} + {s1_ii[33], s1_ii};
    wire signed [34:0] z_im = {s1_ir[33], s1_ir} - {s1_ri[33], s1_ri};

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

    reg mode_train;   // the symbol now entering is a training symbol
    wire stall = out_valid && !out_ready;
    assign bin_ready = resetn && !stall;

    integer k;

    always @(posedge clk) begin
        if (!resetn) begin
            mode_train <= 1'b1;
            trained <= 1'b0;
            train_count <= 16'd0;
            saturation_count <= 32'd0;
            s0_valid <= 1'b0;
            s1_valid <= 1'b0;
            saturation_pending <= 2'd0;
            out_valid <= 1'b0;
            out_re <= 16'sd0;
            out_im <= 16'sd0;
            out_index <= 6'd0;
            out_last <= 1'b0;
            s0_train <= 1'b0;
            s1_train <= 1'b0;
            for (k = 0; k < 64; k = k + 1) begin
                g_re[k] <= 18'sd0;
                g_im[k] <= 18'sd0;
            end
        end else begin
            saturation_count <= saturation_count + saturation_pending;
            saturation_pending <= 2'd0;
            if (retrain)
                mode_train <= 1'b1;

            if (!stall) begin
                // Stage 0.
                s0_valid <= bin_valid;
                if (bin_valid) begin
                    s0_train <= mode_train;
                    s0_re <= bin_re;
                    s0_im <= bin_im;
                    s0_g_re <= g_re[bin_index];
                    s0_g_im <= g_im[bin_index];
                    s0_index <= bin_index;
                    s0_last <= bin_last;
                    if (bin_last && mode_train && !retrain)
                        mode_train <= 1'b0;
                end

                // Stage 1: store the estimate, or form the products.
                s1_valid <= s0_valid && !s0_train;
                s1_train <= s0_train;
                if (s0_valid && s0_train) begin
                    g_re[s0_index] <= est_re;
                    g_im[s0_index] <= est_im;
                    if (s0_last) begin
                        trained <= 1'b1;
                        train_count <= train_count + 16'd1;
                    end
                end
                s1_rr <= s0_re * s0_g_re;
                s1_ii <= s0_im * s0_g_im;
                s1_ir <= s0_im * s0_g_re;
                s1_ri <= s0_re * s0_g_im;
                s1_index <= s0_index;
                s1_last <= s0_last;

                // Stage 2: output.
                out_valid <= s1_valid;
                if (s1_valid) begin
                    out_re <= round_sat(z_re);
                    out_im <= round_sat(z_im);
                    out_index <= s1_index;
                    out_last <= s1_last;
                    saturation_pending <= {1'b0, is_sat(z_re)} + {1'b0, is_sat(z_im)};
                end
            end
        end
    end

endmodule
