`timescale 1ns/1ps

// Block 8 OFDM RTL: fixed-point QPSK mapper matching Lab 8.5.
//
// The Python model maps each serialized bit pair as
//
//   I = +1/sqrt(2) for first bit 0, -1/sqrt(2) for first bit 1
//   Q = +1/sqrt(2) for second bit 0, -1/sqrt(2) for second bit 1
//
// This streaming RTL boundary packs the first/I bit in bits_in[1] and the
// second/Q bit in bits_in[0]. Components are signed Q1.15 with magnitude
// round(32767/sqrt(2)) = 23170, so the ideal symbol energy is approximately
// unity without using the unrepresentable +1.0 endpoint.
//
// Contract:
//   * synchronous active-low reset;
//   * one accepted-clock latency;
//   * valid_out is a one-cycle response to each valid_in;
//   * invalid input cycles do not create output samples;
//   * output data holds its previous value while valid_out is low.
module ofdm_qpsk_mapper (
    input  wire                clk,
    input  wire                resetn,
    input  wire                valid_in,
    input  wire [1:0]          bits_in,
    output reg                 valid_out,
    output reg signed [15:0]   i_out,
    output reg signed [15:0]   q_out
);

    localparam signed [15:0] QPSK_POS = 16'sd23170;
    localparam signed [15:0] QPSK_NEG = -16'sd23170;

    always @(posedge clk) begin
        if (!resetn) begin
            valid_out <= 1'b0;
            i_out <= 16'sd0;
            q_out <= 16'sd0;
        end else begin
            valid_out <= valid_in;
            if (valid_in) begin
                i_out <= bits_in[1] ? QPSK_NEG : QPSK_POS;
                q_out <= bits_in[0] ? QPSK_NEG : QPSK_POS;
            end
        end
    end

endmodule
