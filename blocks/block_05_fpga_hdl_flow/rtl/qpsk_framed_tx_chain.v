// Lab 5.9b - framed QPSK TX chain
//
// QPSK counterpart of bpsk_framed_tx_chain: accepts one framed dibit stream with
// ready/valid/last, maps each dibit to a Gray-coded I/Q symbol, injects a
// deterministic flush tail, and produces the sample-rate pulse-shaped Q1.15 I/Q
// stream. The SPS upsampler and RRC TX FIR are the SAME complex-I/Q blocks used
// by the BPSK chain (they already carry both I and Q; BPSK just left Q = 0).
//
// Same gap-free one-symbol prefetch as the fixed BPSK chain: the mapper runs one
// symbol ahead so the upsampler is never starved and m_valid is emitted on every
// sample-clock cycle of an active burst (no per-symbol handshake bubble).

`timescale 1ns/1ps

module qpsk_framed_tx_chain #(
    parameter integer W = 16,
    parameter integer SPS = 8,
    parameter integer PHASE_W = 3,
    parameter integer FLUSH_SYMBOLS = 16,
    parameter integer COUNT_W = 16,
    parameter COEF_FILE = "blocks/block_05_fpga_hdl_flow/rtl/bpsk_rrc_tx_fir_taps.mem"
) (
    input  wire                 clk,
    input  wire                 rst,
    input  wire                 s_valid,
    input  wire [1:0]           s_dibit,
    input  wire                 s_last,
    output wire                 s_ready,
    output wire                 m_valid,
    output wire signed [W-1:0]  m_i,
    output wire signed [W-1:0]  m_q,
    output wire                 busy
);

reg                mapping = 1'b0;
reg                pf_valid = 1'b0;
reg signed [W-1:0] pf_i = {W{1'b0}};
reg signed [W-1:0] pf_q = {W{1'b0}};

reg                flush_active = 1'b0;
reg [COUNT_W-1:0]  flush_remaining = {COUNT_W{1'b0}};

wire                mapper_out_valid;
wire signed [W-1:0] mapper_out_i;
wire signed [W-1:0] mapper_out_q;
wire                upsampler_in_ready;
wire                upsampler_out_valid;
wire signed [W-1:0] upsampler_out_i;
wire signed [W-1:0] upsampler_out_q;

wire slot_free     = ~mapping && ~pf_valid;
wire map_frame_sym = slot_free && ~flush_active && s_valid;
wire map_flush_sym = slot_free && flush_active;
wire start_map     = map_frame_sym || map_flush_sym;

wire       mapper_in_valid = start_map;
wire [1:0] mapper_in_dibit = map_flush_sym ? 2'b00 : s_dibit;   // flush = (+A,+A)

assign s_ready = slot_free && ~flush_active;
wire upsampler_takes = upsampler_in_ready && pf_valid;

assign busy = flush_active || mapping || pf_valid ||
              upsampler_out_valid || m_valid;

qpsk_symbol_mapper #(
    .W(W)
) symbol_mapper_i (
    .clk(clk),
    .rst(rst),
    .in_valid(mapper_in_valid),
    .in_dibit(mapper_in_dibit),
    .out_valid(mapper_out_valid),
    .out_i(mapper_out_i),
    .out_q(mapper_out_q)
);

bpsk_upsampler_8x #(
    .W(W),
    .SPS(SPS),
    .PHASE_W(PHASE_W)
) upsampler_i (
    .clk(clk),
    .rst(rst),
    .in_valid(pf_valid),
    .in_i(pf_i),
    .in_q(pf_q),
    .in_ready(upsampler_in_ready),
    .out_valid(upsampler_out_valid),
    .out_i(upsampler_out_i),
    .out_q(upsampler_out_q)
);

bpsk_rrc_tx_fir #(
    .W(W),
    .COEF_FILE(COEF_FILE)
) tx_fir_i (
    .clk(clk),
    .rst(rst),
    .in_valid(upsampler_out_valid),
    .in_i(upsampler_out_i),
    .in_q(upsampler_out_q),
    .out_valid(m_valid),
    .out_i(m_i),
    .out_q(m_q)
);

always @(posedge clk) begin
    if (rst) begin
        mapping <= 1'b0;
        pf_valid <= 1'b0;
        pf_i <= {W{1'b0}};
        pf_q <= {W{1'b0}};
        flush_active <= 1'b0;
        flush_remaining <= {COUNT_W{1'b0}};
    end else begin
        if (start_map) begin
            mapping <= 1'b1;
        end else if (mapper_out_valid) begin
            mapping <= 1'b0;
        end

        if (mapper_out_valid) begin
            pf_valid <= 1'b1;
            pf_i <= mapper_out_i;
            pf_q <= mapper_out_q;
        end else if (upsampler_takes) begin
            pf_valid <= 1'b0;
        end

        if (map_frame_sym && s_last) begin
            flush_active <= (FLUSH_SYMBOLS != 0);
            flush_remaining <= FLUSH_SYMBOLS[COUNT_W-1:0];
        end else if (map_flush_sym) begin
            if (flush_remaining <= 1) begin
                flush_active <= 1'b0;
                flush_remaining <= {COUNT_W{1'b0}};
            end else begin
                flush_remaining <= flush_remaining - 1'b1;
            end
        end
    end
end

endmodule
