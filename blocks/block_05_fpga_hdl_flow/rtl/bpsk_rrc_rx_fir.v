// Lab 5.8 - BPSK RRC RX matched filter
//
// Thin wrapper around the shared 65-tap Q1.15 RRC FIR core. The receive side
// uses the same coefficients as the transmit pulse shaper, but the role here
// is matched filtering before timing selection and hard decision.

`timescale 1ns/1ps

module bpsk_rrc_rx_fir #(
    parameter integer W = 16,
    parameter integer CW = 16,
    parameter integer NTAPS = 65,
    parameter integer ACC_W = 40,
    parameter integer SHIFT = 15,
    parameter COEF_FILE = "blocks/block_05_fpga_hdl_flow/rtl/bpsk_rrc_tx_fir_taps.mem"
) (
    input  wire                 clk,
    input  wire                 rst,
    input  wire                 in_valid,
    input  wire signed [W-1:0]  in_i,
    input  wire signed [W-1:0]  in_q,
    output wire                 out_valid,
    output wire signed [W-1:0]  out_i,
    output wire signed [W-1:0]  out_q
);

bpsk_rrc_tx_fir #(
    .W(W),
    .CW(CW),
    .NTAPS(NTAPS),
    .ACC_W(ACC_W),
    .SHIFT(SHIFT),
    .COEF_FILE(COEF_FILE)
) matched_filter_i (
    .clk(clk),
    .rst(rst),
    .in_valid(in_valid),
    .in_i(in_i),
    .in_q(in_q),
    .out_valid(out_valid),
    .out_i(out_i),
    .out_q(out_q)
);

endmodule
