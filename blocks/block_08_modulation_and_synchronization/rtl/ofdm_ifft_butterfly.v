`timescale 1ns/1ps

// Block 8 OFDM RTL: one radix-2 IFFT butterfly matching tools/ofdm_ifft_fixed.py.
//
// Arithmetic contract:
//   * a, b and W are signed Q1.15;
//   * W uses the IFFT sign convention exp(+j*theta);
//   * b*W is formed with widened Q2.30 products, rounded back to a widened
//     Q15-scaled integer without clipping;
//   * outputs are (a +/- b*W)/2 with round-to-nearest, half-LSB ties away
//     from zero;
//   * only the final four output components are saturated to signed Q1.15;
//   * saturation_count reports how many of those four components clipped;
//   * one-cycle valid latency; output payload holds its previous value when
//     valid_in is low;
//   * synchronous active-low reset clears valid and all output registers.
module ofdm_ifft_butterfly (
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

    wire signed [31:0] product_rr = $signed(b_re) * $signed(w_re);
    wire signed [31:0] product_ii = $signed(b_im) * $signed(w_im);
    wire signed [31:0] product_ri = $signed(b_re) * $signed(w_im);
    wire signed [31:0] product_ir = $signed(b_im) * $signed(w_re);

    // One guard bit is required when adding/subtracting two signed 32-bit
    // multiplier products.
    wire signed [32:0] product_rr_ext = {product_rr[31], product_rr};
    wire signed [32:0] product_ii_ext = {product_ii[31], product_ii};
    wire signed [32:0] product_ri_ext = {product_ri[31], product_ri};
    wire signed [32:0] product_ir_ext = {product_ir[31], product_ir};

    wire signed [32:0] twiddle_real_q30 = product_rr_ext - product_ii_ext;
    wire signed [32:0] twiddle_imag_q30 = product_ri_ext + product_ir_ext;

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

    wire signed [17:0] twiddle_re_wide =
        round_q30_to_q15_wide(twiddle_real_q30);
    wire signed [17:0] twiddle_im_wide =
        round_q30_to_q15_wide(twiddle_imag_q30);

    wire signed [18:0] a_re_ext = {{3{a_re[15]}}, a_re};
    wire signed [18:0] a_im_ext = {{3{a_im[15]}}, a_im};
    wire signed [18:0] twiddle_re_ext =
        {twiddle_re_wide[17], twiddle_re_wide};
    wire signed [18:0] twiddle_im_ext =
        {twiddle_im_wide[17], twiddle_im_wide};

    wire signed [18:0] y0_re_scaled =
        round_div2_away(a_re_ext + twiddle_re_ext);
    wire signed [18:0] y0_im_scaled =
        round_div2_away(a_im_ext + twiddle_im_ext);
    wire signed [18:0] y1_re_scaled =
        round_div2_away(a_re_ext - twiddle_re_ext);
    wire signed [18:0] y1_im_scaled =
        round_div2_away(a_im_ext - twiddle_im_ext);

    wire [2:0] saturation_count_next =
        is_saturated_q15(y0_re_scaled) +
        is_saturated_q15(y0_im_scaled) +
        is_saturated_q15(y1_re_scaled) +
        is_saturated_q15(y1_im_scaled);

    always @(posedge clk) begin
        if (!resetn) begin
            valid_out <= 1'b0;
            y0_re <= 16'sd0;
            y0_im <= 16'sd0;
            y1_re <= 16'sd0;
            y1_im <= 16'sd0;
            saturation_count <= 3'd0;
        end else begin
            valid_out <= valid_in;
            if (valid_in) begin
                y0_re <= saturate_q15(y0_re_scaled);
                y0_im <= saturate_q15(y0_im_scaled);
                y1_re <= saturate_q15(y1_re_scaled);
                y1_im <= saturate_q15(y1_im_scaled);
                saturation_count <= saturation_count_next;
            end
        end
    end

endmodule
