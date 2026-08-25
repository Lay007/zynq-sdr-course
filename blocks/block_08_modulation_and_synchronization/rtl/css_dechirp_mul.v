`timescale 1ns/1ps

// Block 8 CSS accelerator: streaming complex dechirp multiplier.
//
// The Python reference in Labs 8.20/8.21 performs
//
//   y = x * conj(reference)
//
// before the FFT. This RTL primitive fixes the first hardware boundary:
//
//   * IQ input and reference components are signed Q1.15;
//   * each real multiplier produces Q2.30;
//   * the complex add/subtract keeps one guard bit (33-bit signed);
//   * the result is arithmetically shifted right by 15 bits;
//   * conversion back to Q1.15 uses truncation plus saturation;
//   * overflow is a one-cycle pulse aligned with valid_out;
//   * latency is one accepted clock; there is no backpressure in this primitive.
//
// The reference inputs are the ordinary upchirp coefficient. Conjugation is
// implemented by the complex multiply signs rather than by modifying the ROM.
module css_dechirp_mul (
    input  wire                    clk,
    input  wire                    resetn,

    input  wire                    valid_in,
    input  wire signed [15:0]      iq_re,
    input  wire signed [15:0]      iq_im,
    input  wire signed [15:0]      ref_re,
    input  wire signed [15:0]      ref_im,

    output reg                     valid_out,
    output reg  signed [15:0]      dechirp_re,
    output reg  signed [15:0]      dechirp_im,
    output reg                     overflow
);

    localparam signed [32:0] Q15_MAX = 33'sd32767;
    localparam signed [32:0] Q15_MIN = -33'sd32768;

    // (a + jb) * conj(c + jd) = (ac + bd) + j(bc - ad)
    wire signed [31:0] product_rr = iq_re * ref_re;
    wire signed [31:0] product_ii = iq_im * ref_im;
    wire signed [31:0] product_ir = iq_im * ref_re;
    wire signed [31:0] product_ri = iq_re * ref_im;

    wire signed [32:0] full_re =
        {product_rr[31], product_rr} + {product_ii[31], product_ii};
    wire signed [32:0] full_im =
        {product_ir[31], product_ir} - {product_ri[31], product_ri};

    // Explicit Q2.30 -> Q1.15 scaling. Arithmetic shift defines truncation for
    // negative values as well; no simulator-dependent implicit cast is used.
    wire signed [32:0] scaled_re = full_re >>> 15;
    wire signed [32:0] scaled_im = full_im >>> 15;

    wire overflow_re = (scaled_re > Q15_MAX) || (scaled_re < Q15_MIN);
    wire overflow_im = (scaled_im > Q15_MAX) || (scaled_im < Q15_MIN);

    wire signed [15:0] clipped_re =
        (scaled_re > Q15_MAX) ? 16'sh7fff :
        (scaled_re < Q15_MIN) ? 16'sh8000 :
        scaled_re[15:0];

    wire signed [15:0] clipped_im =
        (scaled_im > Q15_MAX) ? 16'sh7fff :
        (scaled_im < Q15_MIN) ? 16'sh8000 :
        scaled_im[15:0];

    always @(posedge clk) begin
        if (!resetn) begin
            valid_out   <= 1'b0;
            dechirp_re  <= 16'sd0;
            dechirp_im  <= 16'sd0;
            overflow    <= 1'b0;
        end else begin
            valid_out <= valid_in;
            overflow  <= 1'b0;

            if (valid_in) begin
                dechirp_re <= clipped_re;
                dechirp_im <= clipped_im;
                overflow   <= overflow_re || overflow_im;
            end
        end
    end

endmodule
