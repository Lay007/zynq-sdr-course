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
    input  wire                     adc_input_clk,
    input  wire                     adc_input_reset,
    input  wire                     adc_input_enable,
    input  wire signed [W-1:0]      adc_input_i,
    input  wire signed [W-1:0]      adc_input_q,
    input  wire                     adc_input_valid,
    input  wire signed [W-1:0]      adc_input2_i,
    input  wire signed [W-1:0]      adc_input2_q,
    input  wire                     adc_input2_valid,
    input  wire                     sample_clk,
    input  wire                     sample_resetn,
    input  wire [31:0]              gp_ctrl,
    input  wire [31:0]              gp_frame_bit_count,
    input  wire [31:0]              gp_preamble_count,
    input  wire [31:0]              gp_start_offset,
    output wire [31:0]              gp_status,
    output wire [31:0]              gp_received_bits,
    output wire [31:0]              gp_total_errors,
    output wire [31:0]              gp_signature,
    output wire [31:0]              gp_tx_valid_count,
    output wire [31:0]              gp_rx_valid_count,
    output wire [31:0]              gp_adc_input_debug,
    output wire [31:0]              gp_capture_debug,
    output wire                     tx_path_active,
    output wire [(2*W):0]           tx_sample_bus,
    input  wire [(2*W):0]           rx_sample_bus,
    // Message mailbox (Lab 11.49): the Lab 5.12 register contract, with the modem behind it
    // (zynq_message_mailbox_axi_lite MODE = 1). AXI-Lite slave on the CPU clock; only the low 8
    // address bits reach the core (the interconnect passes the full address, see Lab 5.12).
    input  wire                     s_axi_aclk,
    input  wire                     s_axi_aresetn,
    input  wire [31:0]              s_axi_awaddr,
    input  wire [2:0]               s_axi_awprot,
    input  wire                     s_axi_awvalid,
    output wire                     s_axi_awready,
    input  wire [31:0]              s_axi_wdata,
    input  wire [3:0]               s_axi_wstrb,
    input  wire                     s_axi_wvalid,
    output wire                     s_axi_wready,
    output wire [1:0]               s_axi_bresp,
    output wire                     s_axi_bvalid,
    input  wire                     s_axi_bready,
    input  wire [31:0]              s_axi_araddr,
    input  wire [2:0]               s_axi_arprot,
    input  wire                     s_axi_arvalid,
    output wire                     s_axi_arready,
    output wire [31:0]              s_axi_rdata,
    output wire [1:0]               s_axi_rresp,
    output wire                     s_axi_rvalid,
    input  wire                     s_axi_rready
);

wire                    tx_valid;
wire signed [W-1:0]     tx_i;
wire signed [W-1:0]     tx_q;
wire                    rx_valid;
wire signed [W-1:0]     rx_i;
wire signed [W-1:0]     rx_q;

wire [255:0]            msg_tx_bits;
wire                    msg_tx_toggle;
wire [255:0]            msg_rx_bits;
wire                    msg_rx_toggle;
wire                    msg_rx_locked;

zynq_message_mailbox_axi_lite #(
    .AXI_ADDR_W(8),
    .AXI_DATA_W(32),
    .MODE(1)
) mailbox_i (
    .s_axi_aclk(s_axi_aclk),
    .s_axi_aresetn(s_axi_aresetn),
    .s_axi_awaddr(s_axi_awaddr[7:0]),
    .s_axi_awvalid(s_axi_awvalid),
    .s_axi_awready(s_axi_awready),
    .s_axi_wdata(s_axi_wdata),
    .s_axi_wstrb(s_axi_wstrb),
    .s_axi_wvalid(s_axi_wvalid),
    .s_axi_wready(s_axi_wready),
    .s_axi_bresp(s_axi_bresp),
    .s_axi_bvalid(s_axi_bvalid),
    .s_axi_bready(s_axi_bready),
    .s_axi_araddr(s_axi_araddr[7:0]),
    .s_axi_arvalid(s_axi_arvalid),
    .s_axi_arready(s_axi_arready),
    .s_axi_rdata(s_axi_rdata),
    .s_axi_rresp(s_axi_rresp),
    .s_axi_rvalid(s_axi_rvalid),
    .s_axi_rready(s_axi_rready),
    .modem_tx_bits(msg_tx_bits),
    .modem_tx_toggle(msg_tx_toggle),
    .modem_rx_bits(msg_rx_bits),
    .modem_rx_toggle(msg_rx_toggle),
    .modem_rx_locked(msg_rx_locked)
);

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
    .adc_input_clk(adc_input_clk),
    .adc_input_reset(adc_input_reset),
    .adc_input_enable(adc_input_enable),
    .adc_input_valid(adc_input_valid),
    .adc_input_i(adc_input_i),
    .adc_input_q(adc_input_q),
    .adc_input2_valid(adc_input2_valid),
    .adc_input2_i(adc_input2_i),
    .adc_input2_q(adc_input2_q),
    .sample_clk(sample_clk),
    .sample_resetn(sample_resetn),
    .gp_ctrl(gp_ctrl),
    .gp_frame_bit_count(gp_frame_bit_count),
    .gp_preamble_count(gp_preamble_count),
    .gp_start_offset(gp_start_offset),
    .gp_status(gp_status),
    .gp_received_bits(gp_received_bits),
    .gp_total_errors(gp_total_errors),
    .gp_signature(gp_signature),
    .gp_tx_valid_count(gp_tx_valid_count),
    .gp_rx_valid_count(gp_rx_valid_count),
    .gp_adc_input_debug(gp_adc_input_debug),
    .gp_capture_debug(gp_capture_debug),
    .tx_path_active(tx_path_active),
    .burst_out_valid(tx_valid),
    .burst_out_i(tx_i),
    .burst_out_q(tx_q),
    .capture_in_valid(rx_valid),
    .capture_in_i(rx_i),
    .capture_in_q(rx_q),
    .msg_tx_bits(msg_tx_bits),
    .msg_tx_toggle(msg_tx_toggle),
    .msg_rx_bits(msg_rx_bits),
    .msg_rx_toggle(msg_rx_toggle),
    .msg_rx_locked(msg_rx_locked)
);

endmodule
