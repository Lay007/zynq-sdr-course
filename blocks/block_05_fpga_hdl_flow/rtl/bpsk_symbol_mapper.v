// Lab 5.6 - BPSK symbol mapper
//
// Minimal HDL anchor for the main course route:
// one input bit -> one signed Q1.15 I/Q symbol.
//
// Mapping:
//   bit 0 -> +1.0 + j0  => +32767, 0
//   bit 1 -> -1.0 + j0  => -32767, 0

`timescale 1ns/1ps

module bpsk_symbol_mapper #(
    parameter integer W = 16,
    parameter signed [W-1:0] POS_LEVEL = 16'sd32767,
    parameter signed [W-1:0] NEG_LEVEL = -16'sd32767
) (
    input  wire                 clk,
    input  wire                 rst,
    input  wire                 in_valid,
    input  wire                 in_bit,
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
            out_i <= in_bit ? NEG_LEVEL : POS_LEVEL;
            out_q <= 0;
        end
    end
end

endmodule
