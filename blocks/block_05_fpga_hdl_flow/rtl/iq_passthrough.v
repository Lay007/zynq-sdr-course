// Lab 5.1 — IQ passthrough streaming block
//
// Educational valid-only streaming RTL block.
// The block registers input I/Q samples and propagates in_valid to out_valid
// with one clock cycle of latency.

`timescale 1ns/1ps

module iq_passthrough #(
    parameter integer W = 16
)(
    input  wire                 clk,
    input  wire                 rst,

    input  wire                 in_valid,
    input  wire signed [W-1:0]  in_i,
    input  wire signed [W-1:0]  in_q,

    output reg                  out_valid,
    output reg  signed [W-1:0]  out_i,
    output reg  signed [W-1:0]  out_q
);

always @(posedge clk) begin
    if (rst) begin
        out_valid <= 1'b0;
        out_i     <= {W{1'b0}};
        out_q     <= {W{1'b0}};
    end else begin
        out_valid <= in_valid;
        if (in_valid) begin
            out_i <= in_i;
            out_q <= in_q;
        end
    end
end

endmodule
