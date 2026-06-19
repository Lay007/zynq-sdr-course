// Lab 5.7 - BPSK 8x symbol upsampler
//
// Converts one symbol-rate Q1.15 I/Q sample into eight sample-rate outputs:
// the first sample carries the symbol, the next seven are zeros.
//
// This is the missing multi-rate bridge between the symbol mapper and the
// sample-rate RRC TX FIR in the executable BPSK route.

`timescale 1ns/1ps

module bpsk_upsampler_8x #(
    parameter integer W = 16,
    parameter integer SPS = 8,
    parameter integer PHASE_W = 3
) (
    input  wire                 clk,
    input  wire                 rst,
    input  wire                 in_valid,
    input  wire signed [W-1:0]  in_i,
    input  wire signed [W-1:0]  in_q,
    output wire                 in_ready,
    output reg                  out_valid,
    output reg  signed [W-1:0]  out_i,
    output reg  signed [W-1:0]  out_q
);

reg active = 1'b0;
reg [PHASE_W-1:0] phase = {PHASE_W{1'b0}};

assign in_ready = ~active;

always @(posedge clk) begin
    if (rst) begin
        active <= 1'b0;
        phase <= {PHASE_W{1'b0}};
        out_valid <= 1'b0;
        out_i <= {W{1'b0}};
        out_q <= {W{1'b0}};
    end else begin
        out_valid <= 1'b0;
        out_i <= {W{1'b0}};
        out_q <= {W{1'b0}};

        if (!active) begin
            if (in_valid) begin
                out_valid <= 1'b1;
                out_i <= in_i;
                out_q <= in_q;

                if (SPS > 1) begin
                    active <= 1'b1;
                    phase <= {{(PHASE_W-1){1'b0}}, 1'b1};
                end
            end
        end else begin
            out_valid <= 1'b1;

            if (phase == SPS - 1) begin
                active <= 1'b0;
                phase <= {PHASE_W{1'b0}};
            end else begin
                phase <= phase + 1'b1;
            end
        end
    end
end

endmodule
