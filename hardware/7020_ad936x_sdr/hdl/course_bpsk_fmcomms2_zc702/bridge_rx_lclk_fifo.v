// Small dual-clock (gray-pointer) async FIFO to bring the raw axi_ad9361 ADC
// stream (adc_data_i0/q0 + adc_valid_i0, on l_clk / adc_input_clk) into the
// modem's sample_clk domain.
//
// Why: in AD9361 BIST digital loopback the looped TX data appears on the RAW
// ADC (adc_data_i0) but the vendor util_wfifo (whose dout the bridge normally
// taps as capture_in) does not forward it. Re-routing the RX core from the raw
// ADC through this FIFO makes the deterministic, carrier-offset-free digital
// loopback decodable. Write and read rates are both the AD9361 sample rate, so
// the FIFO self-balances near-empty; on full it drops writes (bounded).
//
// Correct for any l_clk<->sample_clk relationship (synchronous divider or
// asynchronous): standard 2-flop gray-code pointer CDC.

`timescale 1ns/1ps

module bridge_rx_lclk_fifo #(
    parameter integer W = 16,
    parameter integer AW = 5          // depth = 32 samples
) (
    input  wire                 wr_clk,
    input  wire                 wr_rst,      // active-high, wr_clk domain
    input  wire                 wr_en,
    input  wire signed [W-1:0]  wr_i,
    input  wire signed [W-1:0]  wr_q,

    input  wire                 rd_clk,
    input  wire                 rd_rst,      // active-high, rd_clk domain
    output reg                  rd_valid,
    output reg  signed [W-1:0]  rd_i,
    output reg  signed [W-1:0]  rd_q
);

localparam integer DEPTH = (1 << AW);

reg [2*W-1:0] mem [0:DEPTH-1];

// ---- write side (wr_clk) ----
reg  [AW:0] wbin  = {(AW+1){1'b0}};
reg  [AW:0] wgray = {(AW+1){1'b0}};
(* ASYNC_REG = "TRUE" *) reg [AW:0] rgray_wr1 = {(AW+1){1'b0}};
(* ASYNC_REG = "TRUE" *) reg [AW:0] rgray_wr2 = {(AW+1){1'b0}};

wire [AW:0] wbin_next  = wbin + 1'b1;
wire [AW:0] wgray_next = wbin_next ^ (wbin_next >> 1);
// full: next write gray equals read gray with top two bits inverted
wire full = (wgray_next == {~rgray_wr2[AW:AW-1], rgray_wr2[AW-2:0]});

always @(posedge wr_clk) begin
    if (wr_rst) begin
        wbin  <= {(AW+1){1'b0}};
        wgray <= {(AW+1){1'b0}};
        rgray_wr1 <= {(AW+1){1'b0}};
        rgray_wr2 <= {(AW+1){1'b0}};
    end else begin
        rgray_wr1 <= rgray;
        rgray_wr2 <= rgray_wr1;
        if (wr_en && !full) begin
            mem[wbin[AW-1:0]] <= {wr_i, wr_q};
            wbin  <= wbin_next;
            wgray <= wgray_next;
        end
    end
end

// ---- read side (rd_clk) ----
reg  [AW:0] rbin  = {(AW+1){1'b0}};
reg  [AW:0] rgray = {(AW+1){1'b0}};
(* ASYNC_REG = "TRUE" *) reg [AW:0] wgray_rd1 = {(AW+1){1'b0}};
(* ASYNC_REG = "TRUE" *) reg [AW:0] wgray_rd2 = {(AW+1){1'b0}};

wire [AW:0] rbin_next  = rbin + 1'b1;
wire [AW:0] rgray_next = rbin_next ^ (rbin_next >> 1);
wire empty = (rgray == wgray_rd2);

always @(posedge rd_clk) begin
    if (rd_rst) begin
        rbin  <= {(AW+1){1'b0}};
        rgray <= {(AW+1){1'b0}};
        wgray_rd1 <= {(AW+1){1'b0}};
        wgray_rd2 <= {(AW+1){1'b0}};
        rd_valid <= 1'b0;
        rd_i <= {W{1'b0}};
        rd_q <= {W{1'b0}};
    end else begin
        wgray_rd1 <= wgray;
        wgray_rd2 <= wgray_rd1;
        rd_valid <= 1'b0;
        if (!empty) begin
            {rd_i, rd_q} <= mem[rbin[AW-1:0]];
            rd_valid <= 1'b1;
            rbin  <= rbin_next;
            rgray <= rgray_next;
        end
    end
end

endmodule
