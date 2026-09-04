`timescale 1ns/1ps

// Block 8 OFDM RX RTL: scaled 64-point FFT baseline.
//
// The implementation deliberately reuses the verified normalized IFFT core via
// the identity FFT(x)/N = conj(IFFT(conj(x))). Because the IFFT divides by two
// in every radix-2 stage, this wrapper implements the explicit scaled-forward
// transform used by tools/ofdm_fft_fixed.py: numpy.fft.fft(x) / 64.
//
// Q1.15 has an asymmetric endpoint: +32768 is not representable. Conjugating
// an imaginary value of -32768 therefore saturates it to +32767. Those rare
// endpoint clips are counted explicitly and added to the butterfly saturation
// count so the RX path never hides arithmetic overflow.
module ofdm_fft64_sequential (
    input  wire                clk,
    input  wire                resetn,

    input  wire                sample_valid,
    output wire                sample_ready,
    input  wire signed [15:0]  sample_re,
    input  wire signed [15:0]  sample_im,

    output wire                bin_valid,
    input  wire                bin_ready,
    output wire signed [15:0]  bin_re,
    output wire signed [15:0]  bin_im,
    output wire [5:0]          bin_index,
    output wire                bin_last,

    output wire                busy,
    output wire [15:0]         total_saturation_count,
    output reg  [15:0]         conjugation_saturation_count
);

    function automatic signed [15:0] conjugate_imag_q15;
        input signed [15:0] value;
        begin
            if (value == 16'sh8000)
                conjugate_imag_q15 = 16'sh7fff;
            else
                conjugate_imag_q15 = -value;
        end
    endfunction

    wire signed [15:0] ifft_sample_re;
    wire signed [15:0] ifft_sample_im;
    wire               ifft_sample_valid;
    wire [5:0]         ifft_sample_index;
    wire               ifft_sample_last;
    wire [15:0]        ifft_saturation_count;

    wire input_accept = sample_valid && sample_ready;
    wire output_accept = bin_valid && bin_ready;
    wire input_conjugation_clip = input_accept && (sample_im == 16'sh8000);
    wire output_conjugation_clip = output_accept && (ifft_sample_im == 16'sh8000);

    reg [5:0] input_index;

    ofdm_ifft64_sequential normalized_ifft (
        .clk(clk),
        .resetn(resetn),
        .bin_valid(sample_valid),
        .bin_ready(sample_ready),
        .bin_re(sample_re),
        .bin_im(conjugate_imag_q15(sample_im)),
        .sample_valid(ifft_sample_valid),
        .sample_ready(bin_ready),
        .sample_re(ifft_sample_re),
        .sample_im(ifft_sample_im),
        .sample_index(ifft_sample_index),
        .sample_last(ifft_sample_last),
        .busy(busy),
        .total_saturation_count(ifft_saturation_count)
    );

    assign bin_valid = ifft_sample_valid;
    assign bin_re = ifft_sample_re;
    assign bin_im = conjugate_imag_q15(ifft_sample_im);
    assign bin_index = ifft_sample_index;
    assign bin_last = ifft_sample_last;
    assign total_saturation_count =
        ifft_saturation_count + conjugation_saturation_count;

    always @(posedge clk) begin
        if (!resetn) begin
            input_index <= 6'd0;
            conjugation_saturation_count <= 16'd0;
        end else begin
            if (input_accept) begin
                if (input_index == 6'd0)
                    conjugation_saturation_count <= input_conjugation_clip ? 16'd1 : 16'd0;
                else if (input_conjugation_clip)
                    conjugation_saturation_count <= conjugation_saturation_count + 16'd1;

                if (input_index == 6'd63)
                    input_index <= 6'd0;
                else
                    input_index <= input_index + 6'd1;
            end else if (output_conjugation_clip) begin
                conjugation_saturation_count <= conjugation_saturation_count + 16'd1;
            end
        end
    end

endmodule
