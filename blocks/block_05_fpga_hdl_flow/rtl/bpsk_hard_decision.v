// Lab 5.8 - BPSK hard decision
//
// Converts one matched-filtered symbol into a bit with a fixed zero threshold:
// real(sample) >= 0 -> bit 0
// real(sample)  < 0 -> bit 1

`timescale 1ns/1ps

module bpsk_hard_decision #(
    parameter integer W = 16
) (
    input  wire                 clk,
    input  wire                 rst,
    input  wire                 in_valid,
    input  wire signed [W-1:0]  in_i,
    output reg                  out_valid,
    output reg                  out_bit
);

always @(posedge clk) begin
    if (rst) begin
        out_valid <= 1'b0;
        out_bit <= 1'b0;
    end else begin
        out_valid <= in_valid;
        if (in_valid) begin
            out_bit <= (in_i < 0);
        end
    end
end

endmodule
