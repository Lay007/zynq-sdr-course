// Lab 5.9 - BPSK RX bit-recovery wrapper
//
// Bundles the matched filter, fixed-phase timing sampler and hard decision
// into one deterministic receive-side chain.

`timescale 1ns/1ps

module bpsk_rx_bit_recovery_chain #(
    parameter integer W = 16,
    parameter integer SPS = 8,
    parameter integer INDEX_W = 16
) (
    input  wire                     clk,
    input  wire                     rst,
    input  wire                     in_valid,
    input  wire signed [W-1:0]      in_i,
    input  wire signed [W-1:0]      in_q,
    input  wire [INDEX_W-1:0]       start_offset,
    input  wire [INDEX_W-1:0]       symbol_count,
    output wire                     out_valid,
    output wire                     out_bit
);

wire mf_valid;
wire signed [W-1:0] mf_i;
wire signed [W-1:0] mf_q;
wire sym_valid;
wire signed [W-1:0] sym_i;
wire signed [W-1:0] sym_q;

bpsk_rrc_rx_fir matched_filter_i (
    .clk(clk),
    .rst(rst),
    .in_valid(in_valid),
    .in_i(in_i),
    .in_q(in_q),
    .out_valid(mf_valid),
    .out_i(mf_i),
    .out_q(mf_q)
);

bpsk_symbol_timing_sampler #(
    .W(W),
    .SPS(SPS),
    .INDEX_W(INDEX_W)
) timing_sampler_i (
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

bpsk_hard_decision decision_i (
    .clk(clk),
    .rst(rst),
    .in_valid(sym_valid),
    .in_i(sym_i),
    .out_valid(out_valid),
    .out_bit(out_bit)
);

endmodule
