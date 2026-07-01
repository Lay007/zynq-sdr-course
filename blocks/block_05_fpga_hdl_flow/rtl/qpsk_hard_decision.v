// Lab 5.8b - QPSK hard decision
//
// Converts one matched-filtered I/Q symbol into a Gray dibit with a fixed zero
// threshold on each axis (the inverse of qpsk_symbol_mapper):
//   out_dibit[0] = (I < 0)   // I axis
//   out_dibit[1] = (Q < 0)   // Q axis

`timescale 1ns/1ps

module qpsk_hard_decision #(
    parameter integer W = 16
) (
    input  wire                 clk,
    input  wire                 rst,
    input  wire                 in_valid,
    input  wire signed [W-1:0]  in_i,
    input  wire signed [W-1:0]  in_q,
    output reg                  out_valid,
    output reg  [1:0]           out_dibit
);

always @(posedge clk) begin
    if (rst) begin
        out_valid <= 1'b0;
        out_dibit <= 2'b00;
    end else begin
        out_valid <= in_valid;
        if (in_valid) begin
            out_dibit <= {(in_q < 0), (in_i < 0)};
        end
    end
end

endmodule
