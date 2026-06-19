// Lab 5.9 - framed BPSK TX chain
//
// Accepts one framed BPSK bit stream with ready/valid/last, injects a
// deterministic zero-symbol flush tail, and produces the sample-rate
// pulse-shaped Q1.15 stream that can feed a DAC or a loopback receiver.

`timescale 1ns/1ps

module bpsk_framed_tx_chain #(
    parameter integer W = 16,
    parameter integer SPS = 8,
    parameter integer PHASE_W = 3,
    parameter integer FLUSH_SYMBOLS = 16,
    parameter integer COUNT_W = 16
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

reg mapper_in_valid = 1'b0;
reg mapper_in_bit = 1'b0;
reg flush_active = 1'b0;
reg [COUNT_W-1:0] flush_remaining = {COUNT_W{1'b0}};
reg mapper_pending = 1'b0;

wire mapper_out_valid;
wire signed [W-1:0] mapper_out_i;
wire signed [W-1:0] mapper_out_q;
wire upsampler_in_ready;
wire upsampler_out_valid;
wire signed [W-1:0] upsampler_out_i;
wire signed [W-1:0] upsampler_out_q;

wire symbol_launch_ready = ~mapper_pending && upsampler_in_ready;
wire accept_input = s_valid && s_ready;
wire inject_flush_symbol = flush_active && symbol_launch_ready;
wire consume_mapper_symbol = mapper_out_valid && upsampler_in_ready;

assign s_ready = symbol_launch_ready && ~flush_active;
assign busy = flush_active || mapper_pending || mapper_out_valid || upsampler_out_valid || m_valid;

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
    .in_valid(mapper_out_valid),
    .in_i(mapper_out_i),
    .in_q(mapper_out_q),
    .in_ready(upsampler_in_ready),
    .out_valid(upsampler_out_valid),
    .out_i(upsampler_out_i),
    .out_q(upsampler_out_q)
);

bpsk_rrc_tx_fir #(
    .W(W)
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
        mapper_in_valid <= 1'b0;
        mapper_in_bit <= 1'b0;
        flush_active <= 1'b0;
        flush_remaining <= {COUNT_W{1'b0}};
        mapper_pending <= 1'b0;
    end else begin
        mapper_in_valid <= 1'b0;

        if (consume_mapper_symbol) begin
            mapper_pending <= 1'b0;
        end

        if (accept_input) begin
            mapper_in_valid <= 1'b1;
            mapper_in_bit <= s_bit;
            mapper_pending <= 1'b1;

            if (s_last) begin
                flush_active <= (FLUSH_SYMBOLS != 0);
                flush_remaining <= FLUSH_SYMBOLS[COUNT_W-1:0];
            end
        end else if (inject_flush_symbol) begin
            mapper_in_valid <= 1'b1;
            mapper_in_bit <= 1'b0;
            mapper_pending <= 1'b1;

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
