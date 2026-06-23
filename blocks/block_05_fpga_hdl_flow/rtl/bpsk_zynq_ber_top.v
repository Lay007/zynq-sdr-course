// Lab 5.10 - Zynq-ready deterministic BPSK top-level
//
// This top-level keeps the frame source and BER checker inside the FPGA-facing
// logic and exposes the sample-domain TX/RX boundary for later AD9363 or DMA
// integration.

`timescale 1ns/1ps

module bpsk_zynq_ber_top #(
    parameter integer W = 16,
    parameter integer SPS = 8,
    parameter integer INDEX_W = 16,
    parameter integer MAX_FRAME_BITS = 512,
    parameter integer PHASE_W = 3,
    parameter integer FLUSH_SYMBOLS = 16,
    parameter integer RX_IDLE_TIMEOUT_CYCLES = 1048576,
    parameter MEM_FILE = "blocks/block_05_fpga_hdl_flow/rtl/bpsk_frame_bits.mem",
    parameter COEF_FILE = "blocks/block_05_fpga_hdl_flow/rtl/bpsk_rrc_tx_fir_taps.mem"
) (
    input  wire                     clk,
    input  wire                     rst,
    input  wire                     start,
    input  wire [INDEX_W-1:0]       frame_bit_count,
    input  wire [INDEX_W-1:0]       preamble_count,
    input  wire [INDEX_W-1:0]       start_offset,
    output wire                     busy,
    output reg                      done,
    output wire                     tx_valid,
    output wire signed [W-1:0]      tx_i,
    output wire signed [W-1:0]      tx_q,
    input  wire                     rx_valid,
    input  wire signed [W-1:0]      rx_i,
    input  wire signed [W-1:0]      rx_q,
    input  wire [1:0]               rx_decision_mode,
    output reg                      timed_out,
    output wire [INDEX_W-1:0]       received_bits,
    output wire [INDEX_W-1:0]       total_errors,
    output wire [INDEX_W-1:0]       payload_errors,
    output wire                     debug_recovered_valid,
    output wire                     debug_recovered_bit,
    output wire                     debug_symbol_valid,
    output wire signed [W-1:0]      debug_symbol_i
);

localparam integer RX_IDLE_TIMEOUT_W = (RX_IDLE_TIMEOUT_CYCLES <= 1) ? 1 : $clog2(RX_IDLE_TIMEOUT_CYCLES);

wire frame_start = start && !busy;
wire src_valid;
wire src_bit;
wire src_last;
wire src_ready;
wire src_busy;
wire tx_busy;
wire recovered_valid;
wire recovered_bit;
wire ber_busy;
wire ber_done;
reg ber_complete_latched = 1'b0;
reg ber_abort = 1'b0;
reg [RX_IDLE_TIMEOUT_W-1:0] rx_idle_counter = {RX_IDLE_TIMEOUT_W{1'b0}};

assign busy = src_busy || tx_busy || ber_busy;

bpsk_frame_bit_source #(
    .INDEX_W(INDEX_W),
    .MAX_FRAME_BITS(MAX_FRAME_BITS),
    .MEM_FILE(MEM_FILE)
) frame_source_i (
    .clk(clk),
    .rst(rst),
    .start(frame_start),
    .frame_bit_count(frame_bit_count),
    .out_ready(src_ready),
    .out_valid(src_valid),
    .out_bit(src_bit),
    .out_last(src_last),
    .busy(src_busy),
    .done()
);

bpsk_framed_tx_chain #(
    .W(W),
    .SPS(SPS),
    .PHASE_W(PHASE_W),
    .FLUSH_SYMBOLS(FLUSH_SYMBOLS),
    .COUNT_W(INDEX_W),
    .COEF_FILE(COEF_FILE)
) tx_chain_i (
    .clk(clk),
    .rst(rst),
    .s_valid(src_valid),
    .s_bit(src_bit),
    .s_last(src_last),
    .s_ready(src_ready),
    .m_valid(tx_valid),
    .m_i(tx_i),
    .m_q(tx_q),
    .busy(tx_busy)
);

bpsk_rx_bit_recovery_chain #(
    .W(W),
    .SPS(SPS),
    .INDEX_W(INDEX_W),
    .COEF_FILE(COEF_FILE)
) rx_chain_i (
    .clk(clk),
    .rst(rst),
    .in_valid(rx_valid),
    .in_i(rx_i),
    .in_q(rx_q),
    .decision_mode(rx_decision_mode),
    .start_offset(start_offset),
    .symbol_count(frame_bit_count),
    .out_valid(recovered_valid),
    .out_bit(recovered_bit),
    .debug_symbol_valid(debug_symbol_valid),
    .debug_symbol_i(debug_symbol_i)
);

bpsk_ber_counter #(
    .INDEX_W(INDEX_W),
    .MAX_FRAME_BITS(MAX_FRAME_BITS),
    .MEM_FILE(MEM_FILE)
) ber_counter_i (
    .clk(clk),
    .rst(rst),
    .start(frame_start),
    .abort(ber_abort),
    .frame_bit_count(frame_bit_count),
    .preamble_count(preamble_count),
    .in_valid(recovered_valid),
    .in_bit(recovered_bit),
    .busy(ber_busy),
    .done(ber_done),
    .received_bits(received_bits),
    .total_errors(total_errors),
    .payload_errors(payload_errors)
);

always @(posedge clk) begin
    if (rst) begin
        done <= 1'b0;
        timed_out <= 1'b0;
        ber_complete_latched <= 1'b0;
        ber_abort <= 1'b0;
        rx_idle_counter <= {RX_IDLE_TIMEOUT_W{1'b0}};
    end else begin
        done <= 1'b0;
        timed_out <= 1'b0;
        ber_abort <= 1'b0;

        if (frame_start) begin
            ber_complete_latched <= 1'b0;
            rx_idle_counter <= {RX_IDLE_TIMEOUT_W{1'b0}};
        end else if (ber_busy) begin
            if (recovered_valid) begin
                rx_idle_counter <= {RX_IDLE_TIMEOUT_W{1'b0}};
            end else if (RX_IDLE_TIMEOUT_CYCLES <= 1) begin
                ber_abort <= 1'b1;
                timed_out <= 1'b1;
            end else if (rx_idle_counter == RX_IDLE_TIMEOUT_CYCLES - 1) begin
                ber_abort <= 1'b1;
                timed_out <= 1'b1;
            end else begin
                rx_idle_counter <= rx_idle_counter + 1'b1;
            end
        end else begin
            rx_idle_counter <= {RX_IDLE_TIMEOUT_W{1'b0}};
        end

        if (ber_done) begin
            ber_complete_latched <= 1'b1;
        end

        if (ber_complete_latched && !src_busy && !tx_busy && !ber_busy) begin
            done <= 1'b1;
            ber_complete_latched <= 1'b0;
        end
    end
end

assign debug_recovered_valid = recovered_valid;
assign debug_recovered_bit = recovered_bit;

endmodule
