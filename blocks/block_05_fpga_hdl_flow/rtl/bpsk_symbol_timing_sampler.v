// Lab 5.8 - BPSK fixed-phase symbol timing sampler
//
// Selects one complex sample every SPS clocks after a configured start offset.
// This is the deterministic timing anchor used before full synchronizers are
// introduced in later blocks.
//
// symbol_count = all ones means no limit (the listen mode of issue #68/#70 keeps the sampler
// running until its parent ends the attempt). The sample counter then wraps; past_start keeps
// the sampler going after the wrap. For any other symbol_count nothing changes.

`timescale 1ns/1ps

module bpsk_symbol_timing_sampler #(
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
    output reg                      out_valid,
    output reg signed [W-1:0]       out_i,
    output reg signed [W-1:0]       out_q
);

wire unlimited = &symbol_count;
reg  past_start = 1'b0;

reg [INDEX_W-1:0] sample_index = {INDEX_W{1'b0}};
reg [INDEX_W-1:0] emitted_symbols = {INDEX_W{1'b0}};

always @(posedge clk) begin
    if (rst) begin
        sample_index <= {INDEX_W{1'b0}};
        emitted_symbols <= {INDEX_W{1'b0}};
        past_start <= 1'b0;
        out_valid <= 1'b0;
        out_i <= {W{1'b0}};
        out_q <= {W{1'b0}};
    end else begin
        out_valid <= 1'b0;
        out_i <= {W{1'b0}};
        out_q <= {W{1'b0}};

        if (in_valid) begin
            if (
                (past_start || sample_index >= start_offset) &&
                (unlimited || emitted_symbols < symbol_count) &&
                ((sample_index - start_offset) % SPS) == 0
            ) begin
                out_valid <= 1'b1;
                out_i <= in_i;
                out_q <= in_q;
                emitted_symbols <= emitted_symbols + 1'b1;
            end
            sample_index <= sample_index + 1'b1;
            if (sample_index >= start_offset) past_start <= 1'b1;
        end
    end
end

endmodule
