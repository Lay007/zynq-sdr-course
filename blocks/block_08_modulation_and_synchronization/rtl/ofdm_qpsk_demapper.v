`timescale 1ns/1ps

// Block 8 OFDM RX RTL: hard-decision QPSK demapper matching Lab 8.5 and
// ofdm_qpsk_mapper. The first/I bit is bits_out[1], the second/Q bit is
// bits_out[0]. Zero belongs to the positive half-plane, exactly like the
// Python reference (real/imag >= 0 -> bit 0).
//
// This is a transparent ready/valid stage: the upstream source must hold its
// symbol while bits_ready is low, and all metadata remains aligned with it.
module ofdm_qpsk_demapper (
    input  wire                resetn,

    input  wire                symbol_valid,
    output wire                symbol_ready,
    input  wire signed [15:0]  symbol_re,
    input  wire signed [15:0]  symbol_im,
    input  wire [5:0]          data_index,
    input  wire                symbol_last,

    output wire                bits_valid,
    input  wire                bits_ready,
    output wire [1:0]          bits_out,
    output wire [5:0]          bits_index,
    output wire                bits_last
);

    assign symbol_ready = resetn && bits_ready;
    assign bits_valid = resetn && symbol_valid;
    assign bits_out[1] = (symbol_re < 16'sd0);
    assign bits_out[0] = (symbol_im < 16'sd0);
    assign bits_index = data_index;
    assign bits_last = bits_valid && symbol_last;

endmodule
