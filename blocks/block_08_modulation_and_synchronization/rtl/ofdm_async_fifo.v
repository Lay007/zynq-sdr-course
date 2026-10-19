`timescale 1ns/1ps

// Dual-clock FIFO for ofdm_radio_core: Gray-coded pointers, each synchronized into the other domain
// through two flip-flops, so only one pointer bit changes per step and a pointer read mid-change is
// either the old or the new value. Full and empty are therefore pessimistic, never wrong.
// rd_data shows the word at the read pointer while !rd_empty (first word falls through).
// Each side resets only its own pointer; assert both resets together (power-on), never one alone.
// Timing: the Gray pointers cross with set_max_delay -datapath_only (one fast period) in the XDC.
module ofdm_async_fifo #(
    parameter integer W = 32,
    parameter integer AW = 8               // depth 2^AW
) (
    input  wire         wr_clk,
    input  wire         wr_rst,
    input  wire         wr_en,
    input  wire [W-1:0] wr_data,
    output wire         wr_full,
    input  wire         rd_clk,
    input  wire         rd_rst,
    input  wire         rd_en,
    output wire [W-1:0] rd_data,
    output wire         rd_empty
);

reg [W-1:0] mem [0:(1 << AW)-1];

reg  [AW:0] wr_bin = 0, wr_gray = 0, rd_bin = 0, rd_gray = 0;
(* ASYNC_REG = "TRUE" *) reg [AW:0] rd_gray_w1 = 0, rd_gray_w2 = 0;   // read pointer in wr_clk
(* ASYNC_REG = "TRUE" *) reg [AW:0] wr_gray_r1 = 0, wr_gray_r2 = 0;   // write pointer in rd_clk

wire [AW:0] wr_bin_next  = wr_bin + 1'b1;
wire [AW:0] rd_bin_next  = rd_bin + 1'b1;

// full: the write pointer is one lap ahead of the read pointer (Gray: top two bits inverted)
assign wr_full  = (wr_gray == {~rd_gray_w2[AW:AW-1], rd_gray_w2[AW-2:0]});
assign rd_empty = (rd_gray == wr_gray_r2);
assign rd_data  = mem[rd_bin[AW-1:0]];

always @(posedge wr_clk) begin
    if (wr_rst) begin
        wr_bin <= 0;
        wr_gray <= 0;
    end else if (wr_en && !wr_full) begin
        mem[wr_bin[AW-1:0]] <= wr_data;
        wr_bin <= wr_bin_next;
        wr_gray <= wr_bin_next ^ (wr_bin_next >> 1);
    end
    rd_gray_w1 <= rd_gray;
    rd_gray_w2 <= rd_gray_w1;
end

always @(posedge rd_clk) begin
    if (rd_rst) begin
        rd_bin <= 0;
        rd_gray <= 0;
    end else if (rd_en && !rd_empty) begin
        rd_bin <= rd_bin_next;
        rd_gray <= rd_bin_next ^ (rd_bin_next >> 1);
    end
    wr_gray_r1 <= wr_gray;
    wr_gray_r2 <= wr_gray_r1;
end

endmodule
