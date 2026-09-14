`timescale 1ns/1ps

// Block 8 OFDM RX RTL: streaming one-tap complex equalizer.
//
// The correction coefficient W approximates 1/H for the selected subcarrier.
// Samples are signed Q1.15. Coefficients are signed Q2.14 so the baseline can
// represent correction gains up to almost 2.0 without hiding the scale factor.
// The complex product is rounded back to Q1.15 (nearest, half-LSB away from
// zero), then saturated explicitly. saturation_count is cumulative from reset
// and counts clipped I/Q components, not symbols.
//
// Ready/valid contract:
//   * one registered output stage;
//   * input may be accepted when the output register is empty or consumed;
//   * output data and metadata remain stable under downstream backpressure;
//   * synchronous active-low reset clears valid and diagnostics.
module ofdm_one_tap_equalizer (
    input  wire                clk,
    input  wire                resetn,

    input  wire                in_valid,
    output wire                in_ready,
    input  wire signed [15:0]  in_re,
    input  wire signed [15:0]  in_im,
    input  wire signed [15:0]  coeff_re,
    input  wire signed [15:0]  coeff_im,
    input  wire [5:0]          in_index,
    input  wire                in_last,

    output reg                 out_valid,
    input  wire                out_ready,
    output reg signed [15:0]   out_re,
    output reg signed [15:0]   out_im,
    output reg [5:0]           out_index,
    output reg                 out_last,

    output reg [31:0]          saturation_count
);

    wire signed [31:0] product_rr = $signed(in_re) * $signed(coeff_re);
    wire signed [31:0] product_ii = $signed(in_im) * $signed(coeff_im);
    wire signed [31:0] product_ri = $signed(in_re) * $signed(coeff_im);
    wire signed [31:0] product_ir = $signed(in_im) * $signed(coeff_re);

    wire signed [32:0] product_rr_ext = {product_rr[31], product_rr};
    wire signed [32:0] product_ii_ext = {product_ii[31], product_ii};
    wire signed [32:0] product_ri_ext = {product_ri[31], product_ri};
    wire signed [32:0] product_ir_ext = {product_ir[31], product_ir};

    // Q1.15 * Q2.14 -> Q3.29 before the complex add/subtract.
    wire signed [32:0] equalized_re_q29 = product_rr_ext - product_ii_ext;
    wire signed [32:0] equalized_im_q29 = product_ri_ext + product_ir_ext;

    function automatic signed [17:0] round_q29_to_q15_wide;
        input signed [32:0] value;
        reg signed [32:0] magnitude;
        reg signed [32:0] rounded;
        begin
            if (value >= 0) begin
                rounded = (value + 33'sd8192) >>> 14;
                round_q29_to_q15_wide = rounded[17:0];
            end else begin
                magnitude = -value;
                rounded = (magnitude + 33'sd8192) >>> 14;
                round_q29_to_q15_wide = -$signed(rounded[17:0]);
            end
        end
    endfunction

    function automatic signed [15:0] saturate_q15;
        input signed [17:0] value;
        begin
            if (value > 18'sd32767)
                saturate_q15 = 16'sh7fff;
            else if (value < -18'sd32768)
                saturate_q15 = 16'sh8000;
            else
                saturate_q15 = value[15:0];
        end
    endfunction

    function automatic is_saturated_q15;
        input signed [17:0] value;
        begin
            is_saturated_q15 =
                (value > 18'sd32767) || (value < -18'sd32768);
        end
    endfunction

    wire signed [17:0] equalized_re_wide = round_q29_to_q15_wide(equalized_re_q29);
    wire signed [17:0] equalized_im_wide = round_q29_to_q15_wide(equalized_im_q29);
    wire [1:0] saturation_increment =
        is_saturated_q15(equalized_re_wide) +
        is_saturated_q15(equalized_im_wide);

    assign in_ready = resetn && (!out_valid || out_ready);

    always @(posedge clk) begin
        if (!resetn) begin
            out_valid <= 1'b0;
            out_re <= 16'sd0;
            out_im <= 16'sd0;
            out_index <= 6'd0;
            out_last <= 1'b0;
            saturation_count <= 32'd0;
        end else if (in_ready) begin
            out_valid <= in_valid;
            if (in_valid) begin
                out_re <= saturate_q15(equalized_re_wide);
                out_im <= saturate_q15(equalized_im_wide);
                out_index <= in_index;
                out_last <= in_last;
                saturation_count <= saturation_count + saturation_increment;
            end
        end
    end

endmodule
