`timescale 1ns/1ps

// Block 8 OFDM RX RTL: hard-decision 16-QAM slicer, the inverse of
// ofdm_qam16_mapper (bits_out[3:2] from I, bits_out[1:0] from Q).
//
// Per axis: sign bit = (c < 0); inner bit = (-THRESHOLD < c < THRESHOLD).
// The slicer needs every carrier on one amplitude grid, i.e. the zero-forcing
// ofdm_channel_equalizer (NORMALIZE = 1) in front of it. With the 16-QAM
// training symbol sent on the outer points, that equalizer maps the outer
// level 3/sqrt(10) to 2^14/2 = 8192 and the inner level 1/sqrt(10) to 8192/3,
// so the decision threshold halfway between them is 2^14/3 = 5461 (rounded
// down). Any other front-end scaling needs its own THRESHOLD.
//
// Transparent ready/valid stage, like ofdm_qpsk_demapper; metadata stays
// aligned with the symbol.
module ofdm_qam16_demapper #(
    parameter integer THRESHOLD = 5461
) (
    input  wire                resetn,

    input  wire                symbol_valid,
    output wire                symbol_ready,
    input  wire signed [15:0]  symbol_re,
    input  wire signed [15:0]  symbol_im,
    input  wire [5:0]          data_index,
    input  wire                symbol_last,

    output wire                bits_valid,
    input  wire                bits_ready,
    output wire [3:0]          bits_out,
    output wire [5:0]          bits_index,
    output wire                bits_last
);

    localparam signed [16:0] T_POS = THRESHOLD;
    localparam signed [16:0] T_NEG = -THRESHOLD;

    wire signed [16:0] re = symbol_re;
    wire signed [16:0] im = symbol_im;

    assign symbol_ready = resetn && bits_ready;
    assign bits_valid = resetn && symbol_valid;
    assign bits_out[3] = (re < 17'sd0);
    assign bits_out[2] = (re < T_POS) && (re > T_NEG);
    assign bits_out[1] = (im < 17'sd0);
    assign bits_out[0] = (im < T_POS) && (im > T_NEG);
    assign bits_index = data_index;
    assign bits_last = bits_valid && symbol_last;

endmodule
