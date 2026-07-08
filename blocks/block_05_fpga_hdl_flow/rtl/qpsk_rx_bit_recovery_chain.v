// Lab 5.9b - QPSK RX dibit-recovery chain
//
// Reuses the shared complex-I/Q matched filter and fixed-phase symbol timing
// sampler (same blocks as the BPSK RX), then makes a Gray QPSK hard decision:
//   matched filter -> fixed-phase sampler -> qpsk_hard_decision -> dibit.

`timescale 1ns/1ps

module qpsk_rx_bit_recovery_chain #(
    parameter integer W = 16,
    parameter integer SPS = 8,
    parameter integer INDEX_W = 16,
    parameter integer DC_BLOCK_K = 6,
    parameter COEF_FILE = "blocks/block_05_fpga_hdl_flow/rtl/bpsk_rrc_tx_fir_taps.mem"
) (
    input  wire                     clk,
    input  wire                     rst,
    input  wire                     dc_block_en,   // 1 = subtract LO-leakage DC (OTA); 0 = passthrough
    input  wire                     in_valid,
    input  wire signed [W-1:0]      in_i,
    input  wire signed [W-1:0]      in_q,
    input  wire [INDEX_W-1:0]       start_offset,
    input  wire [INDEX_W-1:0]       symbol_count,
    output wire                     out_valid,
    output wire [1:0]               out_dibit,
    output wire                     debug_symbol_valid,
    output wire signed [W-1:0]      debug_symbol_i,
    output wire signed [W-1:0]      debug_symbol_q
);

// DC blocker on the RX sample front: removes the AD9361 LO-leakage DC offset that
// dominates a real over-the-air capture. Passthrough when dc_block_en=0 keeps the
// clean fabric-loopback path effectively unchanged (DC-free input -> ~0 subtracted).
wire dc_valid;
wire signed [W-1:0] dc_i;
wire signed [W-1:0] dc_q;
dc_blocker #(
    .W(W),
    .K(DC_BLOCK_K)
) dc_blocker_i (
    .clk(clk),
    .rst(rst),
    .enable(dc_block_en),
    .in_valid(in_valid),
    .in_i(in_i),
    .in_q(in_q),
    .out_valid(dc_valid),
    .out_i(dc_i),
    .out_q(dc_q)
);

wire mf_valid;
wire signed [W-1:0] mf_i;
wire signed [W-1:0] mf_q;
wire sym_valid;
wire signed [W-1:0] sym_i;
wire signed [W-1:0] sym_q;

bpsk_rrc_rx_fir #(
    .COEF_FILE(COEF_FILE)
) matched_filter_i (
    .clk(clk),
    .rst(rst),
    .in_valid(dc_valid),
    .in_i(dc_i),
    .in_q(dc_q),
    .out_valid(mf_valid),
    .out_i(mf_i),
    .out_q(mf_q)
);

bpsk_symbol_timing_sampler #(
    .W(W),
    .SPS(SPS),
    .INDEX_W(INDEX_W)
) timing_i (
    .clk(clk),
    .rst(rst),
    .in_valid(mf_valid),
    .in_i(mf_i),
    .in_q(mf_q),
    .start_offset(start_offset),
    .symbol_count(symbol_count),
    .out_valid(sym_valid),
    .out_i(sym_i),
    .out_q(sym_q)
);

qpsk_hard_decision decision_i (
    .clk(clk),
    .rst(rst),
    .in_valid(sym_valid),
    .in_i(sym_i),
    .in_q(sym_q),
    .out_valid(out_valid),
    .out_dibit(out_dibit)
);

assign debug_symbol_valid = sym_valid;
assign debug_symbol_i = sym_i;
assign debug_symbol_q = sym_q;

endmodule
