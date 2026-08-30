// Mailbox-field -> packet-v1 -> existing QPSK modem -> packet-v1 -> mailbox-field
// digital loopback. This is synthesizable Stage 3 evidence; it contains no RF,
// AXI interconnect, CDC, or replacement PHY.
//
// One synchronous active-high reset and one clock domain are used. `start` is
// accepted only while busy=0. `done` and `rx_valid` pulse for one clock when the
// decoded mailbox fields are committed.

`timescale 1ns/1ps

module qpsk_packet_digital_loopback #(
    parameter integer W = 16,
    parameter integer SPS = 8,
    parameter integer INDEX_W = 16,
    parameter integer START_OFFSET = 62,
    parameter MEM_FILE = "blocks/block_05_fpga_hdl_flow/rtl/bpsk_frame_bits.mem",
    parameter COEF_FILE = "blocks/block_05_fpga_hdl_flow/rtl/bpsk_rrc_tx_fir_taps.mem"
) (
    input  wire                  clk,
    input  wire                  rst,
    input  wire                  start,
    input  wire [7:0]            tx_length,
    input  wire [15:0]           tx_sequence,
    input  wire [215:0]          tx_payload,
    output wire                  busy,
    output reg                   done,
    output reg                   rx_valid,
    output reg [7:0]             rx_length,
    output reg [15:0]            rx_sequence,
    output reg [215:0]           rx_payload,
    output reg                   rx_crc_ok,
    output reg                   rx_frame_error
);

localparam integer FRAME_SYMBOLS = 140;  // 24 preamble bits + 256 payload bits
localparam integer PREAMBLE_BITS = 24;

reg active = 1'b0;
wire start_accept = start && !active;
assign busy = active;

wire enc_s_ready;
wire enc_m_valid;
wire enc_m_ready;
wire [255:0] encoded_packet;

qpsk_packet_v1_encoder packet_encoder_i (
    .clk(clk), .rst(rst),
    .s_valid(start_accept), .s_ready(enc_s_ready),
    .s_length(tx_length), .s_sequence(tx_sequence), .s_payload(tx_payload),
    .m_valid(enc_m_valid), .m_ready(enc_m_ready), .m_packet(encoded_packet)
);

wire frame_source_busy;
wire frame_source_valid;
wire [1:0] frame_source_dibit;
wire frame_source_last;
wire frame_source_ready;
wire tx_busy;
wire frame_start = enc_m_valid && enc_m_ready;
assign enc_m_ready = !frame_source_busy && !tx_busy;

qpsk_packet_frame_source #(
    .INDEX_W(INDEX_W),
    .PREAMBLE_BITS(PREAMBLE_BITS),
    .MEM_FILE(MEM_FILE)
) frame_source_i (
    .clk(clk), .rst(rst), .start(frame_start), .packet(encoded_packet),
    .out_ready(frame_source_ready), .out_valid(frame_source_valid),
    .out_dibit(frame_source_dibit), .out_last(frame_source_last),
    .busy(frame_source_busy), .done()
);

wire tx_valid;
wire signed [W-1:0] tx_i;
wire signed [W-1:0] tx_q;

qpsk_framed_tx_chain #(
    .W(W), .SPS(SPS), .FLUSH_SYMBOLS(16), .COUNT_W(INDEX_W),
    .COEF_FILE(COEF_FILE)
) tx_chain_i (
    .clk(clk), .rst(rst),
    .s_valid(frame_source_valid), .s_dibit(frame_source_dibit),
    .s_last(frame_source_last), .s_ready(frame_source_ready),
    .m_valid(tx_valid), .m_i(tx_i), .m_q(tx_q), .busy(tx_busy)
);

wire recovered_valid;
wire [1:0] recovered_dibit;

qpsk_rx_bit_recovery_chain #(
    .W(W), .SPS(SPS), .INDEX_W(INDEX_W), .COEF_FILE(COEF_FILE)
) rx_chain_i (
    .clk(clk), .rst(rst || frame_start), .rst_carrier(rst || frame_start),
    .dc_block_en(1'b0), .costas_en(1'b0), .coarse_cfo_en(1'b0),
    .phase_pick_en(1'b0), .timing_recovery_en(1'b0), .diff_en(1'b0),
    .in_valid(tx_valid), .in_i(tx_i), .in_q(tx_q),
    .start_offset(START_OFFSET[INDEX_W-1:0]),
    .symbol_count(FRAME_SYMBOLS[INDEX_W-1:0]),
    .out_valid(recovered_valid), .out_dibit(recovered_dibit),
    .debug_symbol_valid(), .debug_symbol_i(), .debug_symbol_q(),
    .cfo_ready(), .cfo_omega(), .timing_mu(), .timing_omega(), .timing_error()
);

wire payload_bit_valid;
wire payload_bit;
wire frame_sync_busy;

qpsk_ber_counter #(
    .INDEX_W(INDEX_W), .MAX_FRAME_BITS(512),
    .LOCK_PREAMBLE_BITS(PREAMBLE_BITS), .LOCK_ERR_TOL(0), .MEM_FILE(MEM_FILE)
) frame_sync_i (
    .clk(clk), .rst(rst), .start(frame_start), .abort(1'b0),
    .symbol_count(FRAME_SYMBOLS[INDEX_W-1:0]),
    .preamble_count(PREAMBLE_BITS[INDEX_W-1:0]),
    .in_valid(recovered_valid), .in_dibit(recovered_dibit),
    .busy(frame_sync_busy), .done(), .quadrant_swapped(),
    .payload_out_valid(payload_bit_valid), .payload_out_bit(payload_bit),
    .received_symbols(), .total_bit_errors(), .payload_bit_errors(),
    .payload_error_segments(), .first_payload_error_index(),
    .last_payload_error_index()
);

wire collected_valid;
wire collected_ready;
wire [255:0] collected_packet;

qpsk_packet_payload_collector payload_collector_i (
    .clk(clk), .rst(rst), .start(frame_start),
    .in_valid(payload_bit_valid), .in_bit(payload_bit),
    .m_valid(collected_valid), .m_ready(collected_ready),
    .m_packet(collected_packet)
);

wire decoded_valid;
wire [7:0] decoded_length;
wire [15:0] decoded_sequence;
wire [215:0] decoded_payload;
wire decoded_crc_ok;
wire decoded_frame_error;

qpsk_packet_v1_decoder packet_decoder_i (
    .clk(clk), .rst(rst),
    .s_valid(collected_valid), .s_ready(collected_ready), .s_packet(collected_packet),
    .m_valid(decoded_valid), .m_ready(1'b1),
    .m_length(decoded_length), .m_sequence(decoded_sequence),
    .m_payload(decoded_payload), .m_crc_ok(decoded_crc_ok),
    .m_frame_error(decoded_frame_error)
);

always @(posedge clk) begin
    if (rst) begin
        active <= 1'b0;
        done <= 1'b0;
        rx_valid <= 1'b0;
        rx_length <= 8'd0;
        rx_sequence <= 16'd0;
        rx_payload <= 216'd0;
        rx_crc_ok <= 1'b0;
        rx_frame_error <= 1'b0;
    end else begin
        done <= 1'b0;
        rx_valid <= 1'b0;
        if (start_accept && enc_s_ready) active <= 1'b1;
        if (decoded_valid) begin
            active <= 1'b0;
            done <= 1'b1;
            rx_valid <= 1'b1;
            rx_length <= decoded_length;
            rx_sequence <= decoded_sequence;
            rx_payload <= decoded_payload;
            rx_crc_ok <= decoded_crc_ok;
            rx_frame_error <= decoded_frame_error;
        end
    end
end

endmodule
