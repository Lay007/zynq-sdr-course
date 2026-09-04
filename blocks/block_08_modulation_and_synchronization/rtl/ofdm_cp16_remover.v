`timescale 1ns/1ps

// Block 8 OFDM RTL: streaming CP=16 remover for one 80-sample symbol.
//
// Input contract:
//   * exactly 80 accepted Q1.15 complex samples form one CP-protected symbol;
//   * samples 0..15 are the cyclic prefix and are consumed locally;
//   * samples 16..79 are forwarded unchanged as the 64-sample useful symbol;
//   * in_last is expected only on accepted input sample 79.
//
// The payload portion is fully backpressured: once sample 16 is reached,
// input acceptance follows out_ready so no useful sample can be dropped.
// Prefix samples never require downstream readiness because they are discarded.
module ofdm_cp16_remover (
    input  wire               clk,
    input  wire               resetn,

    input  wire signed [15:0] in_i,
    input  wire signed [15:0] in_q,
    input  wire               in_valid,
    output wire               in_ready,
    input  wire               in_last,

    output wire signed [15:0] out_i,
    output wire signed [15:0] out_q,
    output wire               out_valid,
    input  wire               out_ready,
    output wire               out_last,

    output reg                frame_error
);
    reg [6:0] sample_index;

    wire prefix_phase = (sample_index < 7'd16);
    wire accept_in = in_valid && in_ready;
    wire expected_last = (sample_index == 7'd79);

    assign in_ready = prefix_phase ? 1'b1 : out_ready;
    assign out_i = in_i;
    assign out_q = in_q;
    assign out_valid = in_valid && !prefix_phase;
    assign out_last = out_valid && expected_last;

    always @(posedge clk) begin
        if (!resetn) begin
            sample_index <= 7'd0;
            frame_error <= 1'b0;
        end else begin
            frame_error <= 1'b0;

            if (accept_in) begin
                if (in_last != expected_last)
                    frame_error <= 1'b1;

                if (expected_last)
                    sample_index <= 7'd0;
                else
                    sample_index <= sample_index + 7'd1;
            end
        end
    end
endmodule
