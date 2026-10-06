`timescale 1ns/1ps

// Block 8 OFDM RTL: Gray-coded 16-QAM mapper (same interface as
// ofdm_qpsk_mapper, four bits per carrier).
//
// bits_in[3:2] set I and bits_in[1:0] set Q. On each axis the first bit is the
// sign (0 -> positive, as in the QPSK mapper) and the second the magnitude
// (0 -> outer level 3/sqrt(10), 1 -> inner level 1/sqrt(10)):
//     00 -> +3,  01 -> +1,  11 -> -1,  10 -> -3     (neighbours differ in one bit)
// Levels are round(32767 / sqrt(10)) = 10362 and round(3 * 32767 / sqrt(10)) =
// 31086 in Q1.15, so the average symbol energy matches the QPSK mapper's.
// The same mapping is in tools/ofdm_qam16_fixed.py.
//
// Contract: synchronous active-low reset; one clock of latency; valid_out is
// a one-cycle response to each valid_in; outputs hold while valid_out is low.
module ofdm_qam16_mapper (
    input  wire                clk,
    input  wire                resetn,
    input  wire                valid_in,
    input  wire [3:0]          bits_in,
    output reg                 valid_out,
    output reg signed [15:0]   i_out,
    output reg signed [15:0]   q_out
);

    localparam signed [15:0] LEVEL_INNER = 16'sd10362;
    localparam signed [15:0] LEVEL_OUTER = 16'sd31086;

    function automatic signed [15:0] axis_level;
        input [1:0] bits;   // {sign, inner}
        reg signed [15:0] magnitude;
        begin
            magnitude = bits[0] ? LEVEL_INNER : LEVEL_OUTER;
            axis_level = bits[1] ? -magnitude : magnitude;
        end
    endfunction

    always @(posedge clk) begin
        if (!resetn) begin
            valid_out <= 1'b0;
            i_out <= 16'sd0;
            q_out <= 16'sd0;
        end else begin
            valid_out <= valid_in;
            if (valid_in) begin
                i_out <= axis_level(bits_in[3:2]);
                q_out <= axis_level(bits_in[1:0]);
            end
        end
    end

endmodule
