// Lab 5.11 - streaming complex DC blocker (LO-leakage remover) for the RX front.
//
// A real over-the-air AD9361 RX carries a large DC/LO-leakage offset (measured
// |DC| ~= the symbol amplitude on the board's self-OTA capture), which shifts the
// QPSK constellation toward one quadrant. On the single-board coherent link
// (shared 40 MHz reference => TX_LO == RX_LO => CFO ~= 0) that DC is the dominant
// impairment: subtract it and the existing matched filter -> fixed-phase sampler
// -> hard decision -> preamble frame-sync counter recovers BER = 0 (validated
// offline on tmp/qpsk_selfota_a0.npz). No NCO/Costas is needed for one board; the
// full carrier recovery is reserved for the two-board link (independent refs).
//
// Implementation: a per-axis leaky-integrator running mean. The accumulator holds
// mean << K, so dc = acc >>> K converges to the input mean with a time constant of
// ~2^K samples; out = in - dc. K must be large enough to average over several
// symbols (not track the signal): K=4 (tau ~16 = 2 symbols @ SPS=8) still tracks
// the modulation and errs; K>=6 (tau ~64 = 8 symbols) is clean. Enable-gated so the
// DC-free fabric loopback path stays bit-identical (pass-through) at the same latency.

`timescale 1ns/1ps

module dc_blocker #(
    parameter integer W = 16,
    parameter integer K = 6          // running-mean time constant ~ 2^K samples
) (
    input  wire                 clk,
    input  wire                 rst,
    input  wire                 enable,      // 1 = subtract DC, 0 = pass-through
    input  wire                 in_valid,
    input  wire signed [W-1:0]  in_i,
    input  wire signed [W-1:0]  in_q,
    output reg                  out_valid,
    output reg  signed [W-1:0]  out_i,
    output reg  signed [W-1:0]  out_q
);

// Accumulator holds mean << K, so it needs W + K bits plus sign headroom.
reg signed [W+K:0] acc_i;
reg signed [W+K:0] acc_q;

wire signed [W+K:0] acc_i_sr = acc_i >>> K;  // arithmetic shift = acc / 2^K
wire signed [W+K:0] acc_q_sr = acc_q >>> K;
wire signed [W-1:0] dc_i = acc_i_sr[W-1:0];  // steady-state mean fits in W bits
wire signed [W-1:0] dc_q = acc_q_sr[W-1:0];

always @(posedge clk) begin
    if (rst) begin
        acc_i     <= {(W+K+1){1'b0}};
        acc_q     <= {(W+K+1){1'b0}};
        out_valid <= 1'b0;
        out_i     <= {W{1'b0}};
        out_q     <= {W{1'b0}};
    end else begin
        out_valid <= in_valid;
        if (in_valid) begin
            // Leaky integrator: acc += in - (acc >>> K); steady state acc = mean << K.
            // All operands are signed, so the narrower ones are sign-extended.
            acc_i <= acc_i + in_i - dc_i;
            acc_q <= acc_q + in_q - dc_q;
            out_i <= enable ? (in_i - dc_i) : in_i;
            out_q <= enable ? (in_q - dc_q) : in_q;
        end
    end
end

endmodule
