`timescale 1ns/1ps

// Block 8 CSS accelerator: SF7 dechirp front-end.
//
// The caller supplies one Q1.15 complex IQ sample and its modulo-128 sample
// index. The local SF7 reference ROM supplies the ordinary upchirp coefficient;
// css_dechirp_mul performs IQ * conj(reference).
//
// This wrapper intentionally fixes the first accelerator configuration to
// SF=7 and Fs=BW. Later work can generalize the reference generator and symbol
// length without changing the multiplier contract.
module css_sf7_dechirp_frontend (
    input  wire                    clk,
    input  wire                    resetn,
    input  wire                    valid_in,
    input  wire [6:0]              sample_index,
    input  wire signed [15:0]      iq_re,
    input  wire signed [15:0]      iq_im,

    output wire                    valid_out,
    output wire signed [15:0]      dechirp_re,
    output wire signed [15:0]      dechirp_im,
    output wire                    overflow
);

    wire signed [15:0] ref_re;
    wire signed [15:0] ref_im;

    css_sf7_ref_rom u_reference (
        .addr   (sample_index),
        .ref_re (ref_re),
        .ref_im (ref_im)
    );

    css_dechirp_mul u_dechirp (
        .clk        (clk),
        .resetn     (resetn),
        .valid_in   (valid_in),
        .iq_re      (iq_re),
        .iq_im      (iq_im),
        .ref_re     (ref_re),
        .ref_im     (ref_im),
        .valid_out  (valid_out),
        .dechirp_re (dechirp_re),
        .dechirp_im (dechirp_im),
        .overflow   (overflow)
    );

endmodule
