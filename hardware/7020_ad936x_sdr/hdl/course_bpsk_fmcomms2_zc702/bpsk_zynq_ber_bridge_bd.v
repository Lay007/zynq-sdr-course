// Thin BD-facing wrapper around the course BPSK bridge.
//
// IP Integrator module references were inferring unwanted streaming-style
// interfaces from separate valid/I/Q ports. Packing the sample-domain ports
// into plain vectors keeps the BD integration simple while still compiling the
// modem bridge directly from source.

`timescale 1ns/1ps

module bpsk_zynq_ber_bridge_bd #(
    parameter integer W = 16,
    parameter integer SPS = 8,
    parameter integer INDEX_W = 16,
    parameter integer MAX_FRAME_BITS = 512,
    parameter integer PHASE_W = 3,
    parameter integer FLUSH_SYMBOLS = 16,
    parameter MEM_FILE = "bpsk_frame_bits.mem",
    parameter COEF_FILE = "bpsk_rrc_tx_fir_taps.mem"
) (
    input  wire                     ctrl_clk,
    input  wire                     ctrl_resetn,
    input  wire                     sample_clk,
    input  wire                     sample_resetn,
    input  wire [31:0]              gp_ctrl,
    input  wire [31:0]              gp_frame_bit_count,
    input  wire [31:0]              gp_preamble_count,
    input  wire [31:0]              gp_start_offset,
    output wire [31:0]              gp_status,
    output wire [31:0]              gp_received_bits,
    output wire [31:0]              gp_total_errors,
    output wire [31:0]              gp_payload_errors,
    output wire [31:0]              gp_signature,
    output wire                     tx_path_active,
    output wire [(2*W):0]           tx_sample_bus,
    input  wire [(2*W):0]           rx_sample_bus
);

wire                    tx_valid;
wire signed [W-1:0]     tx_i;
wire signed [W-1:0]     tx_q;
wire                    rx_valid;
wire signed [W-1:0]     rx_i;
wire signed [W-1:0]     rx_q;

assign tx_sample_bus = {tx_valid, tx_i, tx_q};
assign rx_valid = rx_sample_bus[2*W];
assign rx_i = rx_sample_bus[(2*W)-1:W];
assign rx_q = rx_sample_bus[W-1:0];

bpsk_zynq_ber_gpreg_bridge #(
    .W(W),
    .SPS(SPS),
    .INDEX_W(INDEX_W),
    .MAX_FRAME_BITS(MAX_FRAME_BITS),
    .PHASE_W(PHASE_W),
    .FLUSH_SYMBOLS(FLUSH_SYMBOLS),
    .MEM_FILE(MEM_FILE),
    .COEF_FILE(COEF_FILE)
) inst (
    .ctrl_clk(ctrl_clk),
    .ctrl_resetn(ctrl_resetn),
    .sample_clk(sample_clk),
    .sample_resetn(sample_resetn),
    .gp_ctrl(gp_ctrl),
    .gp_frame_bit_count(gp_frame_bit_count),
    .gp_preamble_count(gp_preamble_count),
    .gp_start_offset(gp_start_offset),
    .gp_status(gp_status),
    .gp_received_bits(gp_received_bits),
    .gp_total_errors(gp_total_errors),
    .gp_payload_errors(gp_payload_errors),
    .gp_signature(gp_signature),
    .tx_path_active(tx_path_active),
    .burst_out_valid(tx_valid),
    .burst_out_i(tx_i),
    .burst_out_q(tx_q),
    .capture_in_valid(rx_valid),
    .capture_in_i(rx_i),
    .capture_in_q(rx_q)
);

endmodule
