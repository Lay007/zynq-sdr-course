// Lab 5.9 - framed BPSK TX chain
//
// Accepts one framed BPSK bit stream with ready/valid/last, injects a
// deterministic zero-symbol flush tail, and produces the sample-rate
// pulse-shaped Q1.15 stream that can feed a DAC or a loopback receiver.
//
// Gap-free intake: a one-symbol prefetch register keeps the SPS upsampler
// continuously fed so `m_valid` is asserted on EVERY sample-clock cycle of an
// active burst (no per-symbol handshake bubble). A bursty TX stream would
// under-run a continuously-draining DAC FIFO (util_rfifo) and warp the played
// waveform non-uniformly; a gap-free stream matches the DAC consumption rate
// one-to-one. The logical symbol/sample sequence is identical to the previous
// bubbled version, so simulation BER is unchanged.

`timescale 1ns/1ps

module bpsk_framed_tx_chain #(
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
    input  wire                 s_bit,
    input  wire                 s_last,
    output wire                 s_ready,
    output wire                 m_valid,
    output wire signed [W-1:0]  m_i,
    output wire signed [W-1:0]  m_q,
    output wire                 busy
);

// --- symbol intake pipeline with a one-symbol prefetch ---
// The mapper maps a symbol (1-cycle latency) into a 1-deep prefetch register
// `pf_*`. The SPS upsampler consumes the prefetch the instant it becomes ready
// (~every SPS cycles), and the prefetch refills within ~2 cycles, so it is
// always full well before the upsampler asks again -> no output bubble.

reg                 mapping = 1'b0;          // a symbol is in the 1-cycle mapper
reg                 pf_valid = 1'b0;         // prefetch register holds a symbol
reg signed [W-1:0]  pf_i = {W{1'b0}};
reg signed [W-1:0]  pf_q = {W{1'b0}};

reg                 flush_active = 1'b0;
reg [COUNT_W-1:0]   flush_remaining = {COUNT_W{1'b0}};

wire                mapper_out_valid;
wire signed [W-1:0] mapper_out_i;
wire signed [W-1:0] mapper_out_q;
wire                upsampler_in_ready;
wire                upsampler_out_valid;
wire signed [W-1:0] upsampler_out_i;
wire signed [W-1:0] upsampler_out_q;

// A symbol slot is free to start a new map only when nothing is in flight and
// the prefetch register is empty.
wire slot_free       = ~mapping && ~pf_valid;
// Start mapping the next symbol: a frame bit while not flushing, or a flush
// zero-symbol while the flush tail is active.
wire map_frame_bit   = slot_free && ~flush_active && s_valid;
wire map_flush_sym   = slot_free && flush_active;
wire start_map       = map_frame_bit || map_flush_sym;

wire mapper_in_valid = start_map;
wire mapper_in_bit   = map_flush_sym ? 1'b0 : s_bit;

// Frame bit is accepted exactly when a frame map starts.
assign s_ready = slot_free && ~flush_active;

// The upsampler takes the prefetched symbol when it is both ready and full.
wire upsampler_takes = upsampler_in_ready && pf_valid;

assign busy = flush_active || mapping || pf_valid ||
              upsampler_out_valid || m_valid;

bpsk_symbol_mapper #(
    .W(W)
) symbol_mapper_i (
    .clk(clk),
    .rst(rst),
    .in_valid(mapper_in_valid),
    .in_bit(mapper_in_bit),
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
        // map-in-flight tracking (mapper has a 1-cycle latency)
        if (start_map) begin
            mapping <= 1'b1;
        end else if (mapper_out_valid) begin
            mapping <= 1'b0;
        end

        // prefetch register: refill from the mapper, drain to the upsampler
        if (mapper_out_valid) begin
            pf_valid <= 1'b1;
            pf_i <= mapper_out_i;
            pf_q <= mapper_out_q;
        end else if (upsampler_takes) begin
            pf_valid <= 1'b0;
        end

        // flush tail bookkeeping: arm on the last frame bit, then count down
        // one flush symbol per flush map.
        if (map_frame_bit && s_last) begin
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
