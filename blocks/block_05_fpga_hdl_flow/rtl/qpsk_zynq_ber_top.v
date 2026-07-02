// Lab 5.10b - Zynq-ready deterministic QPSK BER top-level
//
// QPSK counterpart of bpsk_zynq_ber_top: framed dibit source -> QPSK TX chain ->
// (external loopback tx->rx) -> QPSK RX dibit recovery -> QPSK BER counter. The
// SPS upsampler, RRC TX/RX FIRs and fixed-phase timing sampler are the shared
// complex-I/Q blocks; only the mapper / decision / BER stages are QPSK-specific.

`timescale 1ns/1ps

module qpsk_zynq_ber_top #(
    parameter integer W = 16,
    parameter integer SPS = 8,
    parameter integer INDEX_W = 16,
    parameter integer MAX_FRAME_BITS = 512,
    parameter integer PHASE_W = 3,
    parameter integer FLUSH_SYMBOLS = 16,
    parameter integer RX_IDLE_TIMEOUT_CYCLES = 4096,
    parameter MEM_FILE = "blocks/block_05_fpga_hdl_flow/rtl/bpsk_frame_bits.mem",
    parameter COEF_FILE = "blocks/block_05_fpga_hdl_flow/rtl/bpsk_rrc_tx_fir_taps.mem"
) (
    input  wire                     clk,
    input  wire                     rst,
    input  wire                     start,
    input  wire [INDEX_W-1:0]       symbol_count,   // QPSK symbols (2 bits each)
    input  wire [INDEX_W-1:0]       preamble_count, // preamble length in BITS (frame-sync)
    input  wire [INDEX_W-1:0]       start_offset,
    output wire                     busy,
    output reg                      done,
    output wire                     tx_valid,
    output wire signed [W-1:0]      tx_i,
    output wire signed [W-1:0]      tx_q,
    input  wire                     rx_valid,
    input  wire signed [W-1:0]      rx_i,
    input  wire signed [W-1:0]      rx_q,
    output reg                      timed_out,
    output wire [INDEX_W-1:0]       received_symbols,
    output wire [INDEX_W-1:0]       total_bit_errors,
    output wire                     debug_symbol_valid,
    output wire signed [W-1:0]      debug_symbol_i,
    output wire signed [W-1:0]      debug_symbol_q
);

localparam integer RX_IDLE_TIMEOUT_W = (RX_IDLE_TIMEOUT_CYCLES <= 1) ? 1 : $clog2(RX_IDLE_TIMEOUT_CYCLES);

wire frame_start = start && !busy;
wire src_valid;
wire [1:0] src_dibit;
wire src_last;
wire src_ready;
wire src_busy;
wire tx_busy;
wire recovered_valid;
wire [1:0] recovered_dibit;
wire ber_busy;
wire ber_done;
reg ber_abort = 1'b0;
reg [RX_IDLE_TIMEOUT_W-1:0] rx_idle_counter = {RX_IDLE_TIMEOUT_W{1'b0}};

assign busy = src_busy || tx_busy || ber_busy;

qpsk_frame_dibit_source #(
    .INDEX_W(INDEX_W),
    .MAX_FRAME_BITS(MAX_FRAME_BITS),
    .MEM_FILE(MEM_FILE)
) source_i (
    .clk(clk),
    .rst(rst),
    .start(frame_start),
    .symbol_count(symbol_count),
    .out_ready(src_ready),
    .out_valid(src_valid),
    .out_dibit(src_dibit),
    .out_last(src_last),
    .busy(src_busy),
    .done()
);

qpsk_framed_tx_chain #(
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
    .s_dibit(src_dibit),
    .s_last(src_last),
    .s_ready(src_ready),
    .m_valid(tx_valid),
    .m_i(tx_i),
    .m_q(tx_q),
    .busy(tx_busy)
);

qpsk_rx_bit_recovery_chain #(
    .W(W),
    .SPS(SPS),
    .INDEX_W(INDEX_W),
    .COEF_FILE(COEF_FILE)
) rx_chain_i (
    .clk(clk),
    // restart the matched filter + sampler each frame so back-to-back bursts realign
    .rst(rst || frame_start),
    .in_valid(rx_valid),
    .in_i(rx_i),
    .in_q(rx_q),
    .start_offset(start_offset),
    .symbol_count(symbol_count),
    .out_valid(recovered_valid),
    .out_dibit(recovered_dibit),
    .debug_symbol_valid(debug_symbol_valid),
    .debug_symbol_i(debug_symbol_i),
    .debug_symbol_q(debug_symbol_q)
);

qpsk_ber_counter #(
    .INDEX_W(INDEX_W),
    .MAX_FRAME_BITS(MAX_FRAME_BITS),
    .MEM_FILE(MEM_FILE)
) ber_counter_i (
    .clk(clk),
    .rst(rst),
    .start(frame_start),
    .abort(ber_abort),
    .symbol_count(symbol_count),
    .preamble_count(preamble_count),
    .in_valid(recovered_valid),
    .in_dibit(recovered_dibit),
    .busy(ber_busy),
    .done(ber_done),
    .received_symbols(received_symbols),
    .total_bit_errors(total_bit_errors)
);

always @(posedge clk) begin
    if (rst) begin
        done <= 1'b0;
        timed_out <= 1'b0;
        ber_abort <= 1'b0;
        rx_idle_counter <= {RX_IDLE_TIMEOUT_W{1'b0}};
    end else begin
        done <= 1'b0;
        timed_out <= 1'b0;
        ber_abort <= 1'b0;

        if (frame_start) begin
            rx_idle_counter <= {RX_IDLE_TIMEOUT_W{1'b0}};
        end else if (ber_busy) begin
            if (recovered_valid) begin
                rx_idle_counter <= {RX_IDLE_TIMEOUT_W{1'b0}};
            end else if (rx_idle_counter == RX_IDLE_TIMEOUT_CYCLES - 1) begin
                ber_abort <= 1'b1;
                timed_out <= 1'b1;
            end else begin
                rx_idle_counter <= rx_idle_counter + 1'b1;
            end
        end

        if (ber_done) begin
            done <= 1'b1;
        end
    end
end

endmodule
