// Lab 5.6b - QPSK symbol mapper (Gray-coded)
//
// Two input bits -> one signed Q1.15 I/Q symbol. QPSK is two independent BPSK
// axes: the low bit drives I, the high bit drives Q, so flipping either bit moves
// to an adjacent constellation point (one axis flip = one bit change) -> Gray code.
//
//   dibit b1 b0 -> (I, Q)
//   0 0 -> (+A, +A)      0 1 -> (-A, +A)
//   1 0 -> (+A, -A)      1 1 -> (-A, -A)
//
// Per-axis amplitude A = round(32767 / sqrt(2)) = 23170, so the symbol magnitude
// |I + jQ| = A*sqrt(2) ~= 32767 matches the full-scale BPSK symbol energy. Same
// one-cycle latency and ready/valid-free streaming shape as bpsk_symbol_mapper, so
// it drops into the existing upsampler -> RRC -> DAC chain unchanged.

`timescale 1ns/1ps

module qpsk_symbol_mapper #(
    parameter integer W = 16,
    parameter signed [W-1:0] POS_LEVEL = 16'sd23170,
    parameter signed [W-1:0] NEG_LEVEL = -16'sd23170
) (
    input  wire                 clk,
    input  wire                 rst,
    input  wire                 in_valid,
    input  wire [1:0]           in_dibit,   // in_dibit[0] -> I, in_dibit[1] -> Q
    output reg                  out_valid,
    output reg signed [W-1:0]   out_i,
    output reg signed [W-1:0]   out_q
);

always @(posedge clk) begin
    if (rst) begin
        out_valid <= 1'b0;
        out_i <= 0;
        out_q <= 0;
    end else begin
        out_valid <= in_valid;

        if (in_valid) begin
            out_i <= in_dibit[0] ? NEG_LEVEL : POS_LEVEL;
            out_q <= in_dibit[1] ? NEG_LEVEL : POS_LEVEL;
        end
    end
end

endmodule
