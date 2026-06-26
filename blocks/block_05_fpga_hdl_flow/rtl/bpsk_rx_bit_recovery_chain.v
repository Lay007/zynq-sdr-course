// Lab 5.9 - BPSK RX bit-recovery wrapper
//
// Bundles the matched filter, fixed-phase timing sampler and hard decision
// into one deterministic receive-side chain.

`timescale 1ns/1ps

module bpsk_rx_bit_recovery_chain #(
    parameter integer W = 16,
    parameter integer SPS = 8,
    parameter integer INDEX_W = 16,
    // 0 = fixed-phase decimator (Lab 5.8, deterministic; used by the Block-5 labs)
    // 1 = Gardner timing-recovery loop (tracks SPS/timing drift; used by the runtime
    //     AD9361 bridge where the sample path is not exactly 8 samples/symbol)
    parameter integer TIMING_RECOVERY = 0,
    parameter COEF_FILE = "blocks/block_05_fpga_hdl_flow/rtl/bpsk_rrc_tx_fir_taps.mem"
) (
    input  wire                     clk,
    input  wire                     rst,
    input  wire                     in_valid,
    input  wire signed [W-1:0]      in_i,
    input  wire signed [W-1:0]      in_q,
    input  wire [1:0]               decision_mode,
    input  wire [INDEX_W-1:0]       start_offset,
    input  wire [INDEX_W-1:0]       symbol_count,
    output wire                     out_valid,
    output wire                     out_bit,
    output wire                     debug_symbol_valid,
    output wire signed [W-1:0]      debug_symbol_i
);

wire mf_valid;
wire signed [W-1:0] mf_i;
wire signed [W-1:0] mf_q;
wire sym_valid;
wire signed [W-1:0] sym_i;
wire signed [W-1:0] sym_q;
wire signed [W-1:0] decision_sample;

bpsk_rrc_rx_fir #(
    .COEF_FILE(COEF_FILE)
) matched_filter_i (
    .clk(clk),
    .rst(rst),
    .in_valid(in_valid),
    .in_i(in_i),
    .in_q(in_q),
    .out_valid(mf_valid),
    .out_i(mf_i),
    .out_q(mf_q)
);

generate
if (TIMING_RECOVERY == 0) begin : g_fixed_phase
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
end else begin : g_timing_recovery
    bpsk_symbol_timing_recovery #(
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
end
endgenerate

assign decision_sample =
    (decision_mode == 2'b00) ? sym_i :
    (decision_mode == 2'b01) ? -sym_i :
    (decision_mode == 2'b10) ? sym_q :
                               -sym_q;

bpsk_hard_decision decision_i (
    .clk(clk),
    .rst(rst),
    .in_valid(sym_valid),
    .in_i(decision_sample),
    .out_valid(out_valid),
    .out_bit(out_bit)
);

assign debug_symbol_valid = sym_valid;
assign debug_symbol_i = decision_sample;

endmodule
