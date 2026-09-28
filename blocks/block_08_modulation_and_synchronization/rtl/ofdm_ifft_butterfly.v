`timescale 1ns/1ps

// Block 8 OFDM RTL: one radix-2 IFFT butterfly matching tools/ofdm_ifft_fixed.py.
//
// Arithmetic contract (identical for both PIPELINED settings):
//   * a, b and W are signed Q1.15;
//   * W uses the IFFT sign convention exp(+j*theta);
//   * b*W is formed with widened Q2.30 products, rounded back to a widened
//     Q15-scaled integer without clipping;
//   * outputs are (a +/- b*W)/2 with round-to-nearest, half-LSB ties away
//     from zero;
//   * only the final four output components are saturated to signed Q1.15;
//   * saturation_count reports how many of those four components clipped;
//   * output payload holds its previous value when no result is produced;
//   * synchronous active-low reset clears valid and all registers.
//
// Timing contract:
//   * PIPELINED = 0: one-cycle valid latency; the whole datapath (multiply,
//     twiddle rounding, add, halve, saturate) sits between one register pair.
//     This is the teaching baseline.
//   * PIPELINED = 1: four-cycle valid latency and one result per clock:
//     inputs are registered (so the caller's memory/twiddle selection is cut
//     off), then the four products, then the rounded twiddle product, then the
//     halved and saturated outputs. Vivado 2021.1 measured the baseline's
//     critical path at 28 logic levels / about 20 ns inside the 64-point
//     transforms; these registers split it.
module ofdm_ifft_butterfly #(
    parameter integer PIPELINED = 0
) (
    input  wire                clk,
    input  wire                resetn,
    input  wire                valid_in,

    input  wire signed [15:0]  a_re,
    input  wire signed [15:0]  a_im,
    input  wire signed [15:0]  b_re,
    input  wire signed [15:0]  b_im,
    input  wire signed [15:0]  w_re,
    input  wire signed [15:0]  w_im,

    output reg                 valid_out,
    output reg signed [15:0]   y0_re,
    output reg signed [15:0]   y0_im,
    output reg signed [15:0]   y1_re,
    output reg signed [15:0]   y1_im,
    output reg [2:0]           saturation_count
);

    function automatic signed [17:0] round_q30_to_q15_wide;
        input signed [32:0] value;
        reg signed [32:0] magnitude;
        reg signed [32:0] rounded;
        begin
            if (value >= 0) begin
                rounded = (value + 33'sd16384) >>> 15;
                round_q30_to_q15_wide = rounded[17:0];
            end else begin
                magnitude = -value;
                rounded = (magnitude + 33'sd16384) >>> 15;
                round_q30_to_q15_wide = -$signed(rounded[17:0]);
            end
        end
    endfunction

    function automatic signed [18:0] round_div2_away;
        input signed [18:0] value;
        reg signed [18:0] magnitude;
        begin
            if (value >= 0) begin
                round_div2_away = (value + 19'sd1) >>> 1;
            end else begin
                magnitude = -value;
                round_div2_away = -$signed((magnitude + 19'sd1) >>> 1);
            end
        end
    endfunction

    function automatic signed [15:0] saturate_q15;
        input signed [18:0] value;
        begin
            if (value > 19'sd32767)
                saturate_q15 = 16'sh7fff;
            else if (value < -19'sd32768)
                saturate_q15 = 16'sh8000;
            else
                saturate_q15 = value[15:0];
        end
    endfunction

    function automatic is_saturated_q15;
        input signed [18:0] value;
        begin
            is_saturated_q15 =
                (value > 19'sd32767) || (value < -19'sd32768);
        end
    endfunction

    // One guard bit is required when adding/subtracting two signed 32-bit
    // multiplier products.
    function automatic signed [17:0] twiddle_real_rounded;
        input signed [31:0] product_rr;
        input signed [31:0] product_ii;
        begin
            twiddle_real_rounded = round_q30_to_q15_wide(
                {product_rr[31], product_rr} - {product_ii[31], product_ii});
        end
    endfunction

    function automatic signed [17:0] twiddle_imag_rounded;
        input signed [31:0] product_ri;
        input signed [31:0] product_ir;
        begin
            twiddle_imag_rounded = round_q30_to_q15_wide(
                {product_ri[31], product_ri} + {product_ir[31], product_ir});
        end
    endfunction

    // Output stage shared by both variants: (a +/- twiddle) / 2, saturated.
    reg signed [15:0] final_a_re;
    reg signed [15:0] final_a_im;
    reg signed [17:0] final_tw_re;
    reg signed [17:0] final_tw_im;

    wire signed [18:0] a_re_ext = {{3{final_a_re[15]}}, final_a_re};
    wire signed [18:0] a_im_ext = {{3{final_a_im[15]}}, final_a_im};
    wire signed [18:0] twiddle_re_ext = {final_tw_re[17], final_tw_re};
    wire signed [18:0] twiddle_im_ext = {final_tw_im[17], final_tw_im};

    wire signed [18:0] y0_re_scaled = round_div2_away(a_re_ext + twiddle_re_ext);
    wire signed [18:0] y0_im_scaled = round_div2_away(a_im_ext + twiddle_im_ext);
    wire signed [18:0] y1_re_scaled = round_div2_away(a_re_ext - twiddle_re_ext);
    wire signed [18:0] y1_im_scaled = round_div2_away(a_im_ext - twiddle_im_ext);

    wire [2:0] saturation_count_next =
        is_saturated_q15(y0_re_scaled) +
        is_saturated_q15(y0_im_scaled) +
        is_saturated_q15(y1_re_scaled) +
        is_saturated_q15(y1_im_scaled);

    wire final_valid;

    always @(posedge clk) begin
        if (!resetn) begin
            valid_out <= 1'b0;
            y0_re <= 16'sd0;
            y0_im <= 16'sd0;
            y1_re <= 16'sd0;
            y1_im <= 16'sd0;
            saturation_count <= 3'd0;
        end else begin
            valid_out <= final_valid;
            if (final_valid) begin
                y0_re <= saturate_q15(y0_re_scaled);
                y0_im <= saturate_q15(y0_im_scaled);
                y1_re <= saturate_q15(y1_re_scaled);
                y1_im <= saturate_q15(y1_im_scaled);
                saturation_count <= saturation_count_next;
            end
        end
    end

    generate
        if (PIPELINED == 0) begin : g_single_cycle
            assign final_valid = valid_in;
            always @* begin
                final_a_re = a_re;
                final_a_im = a_im;
                final_tw_re = twiddle_real_rounded(
                    $signed(b_re) * $signed(w_re), $signed(b_im) * $signed(w_im));
                final_tw_im = twiddle_imag_rounded(
                    $signed(b_re) * $signed(w_im), $signed(b_im) * $signed(w_re));
            end
        end else begin : g_pipelined
            // Stage 0: registered inputs.
            reg s0_valid;
            reg signed [15:0] s0_a_re, s0_a_im, s0_b_re, s0_b_im, s0_w_re, s0_w_im;
            // Stage 1: registered products.
            reg s1_valid;
            reg signed [15:0] s1_a_re, s1_a_im;
            reg signed [31:0] s1_rr, s1_ii, s1_ri, s1_ir;
            // Stage 2: registered, rounded twiddle product.
            reg s2_valid;
            reg signed [15:0] s2_a_re, s2_a_im;
            reg signed [17:0] s2_tw_re, s2_tw_im;

            assign final_valid = s2_valid;
            always @* begin
                final_a_re = s2_a_re;
                final_a_im = s2_a_im;
                final_tw_re = s2_tw_re;
                final_tw_im = s2_tw_im;
            end

            always @(posedge clk) begin
                if (!resetn) begin
                    s0_valid <= 1'b0;
                    s1_valid <= 1'b0;
                    s2_valid <= 1'b0;
                    s0_a_re <= 16'sd0; s0_a_im <= 16'sd0;
                    s0_b_re <= 16'sd0; s0_b_im <= 16'sd0;
                    s0_w_re <= 16'sd0; s0_w_im <= 16'sd0;
                    s1_a_re <= 16'sd0; s1_a_im <= 16'sd0;
                    s1_rr <= 32'sd0; s1_ii <= 32'sd0; s1_ri <= 32'sd0; s1_ir <= 32'sd0;
                    s2_a_re <= 16'sd0; s2_a_im <= 16'sd0;
                    s2_tw_re <= 18'sd0; s2_tw_im <= 18'sd0;
                end else begin
                    s0_valid <= valid_in;
                    s1_valid <= s0_valid;
                    s2_valid <= s1_valid;
                    if (valid_in) begin
                        s0_a_re <= a_re; s0_a_im <= a_im;
                        s0_b_re <= b_re; s0_b_im <= b_im;
                        s0_w_re <= w_re; s0_w_im <= w_im;
                    end
                    if (s0_valid) begin
                        s1_a_re <= s0_a_re; s1_a_im <= s0_a_im;
                        s1_rr <= s0_b_re * s0_w_re;
                        s1_ii <= s0_b_im * s0_w_im;
                        s1_ri <= s0_b_re * s0_w_im;
                        s1_ir <= s0_b_im * s0_w_re;
                    end
                    if (s1_valid) begin
                        s2_a_re <= s1_a_re; s2_a_im <= s1_a_im;
                        s2_tw_re <= twiddle_real_rounded(s1_rr, s1_ii);
                        s2_tw_im <= twiddle_imag_rounded(s1_ri, s1_ir);
                    end
                end
            end
        end
    endgenerate

endmodule
