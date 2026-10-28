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
// ~2^K samples; out = in - dc. Enable-gated so the DC-free fabric loopback path stays
// bit-identical (pass-through) at the same latency.
//
// K is a direct trade: too small and the estimate follows the modulation instead of the
// DC, too large and it cannot converge inside a burst. The earlier per-frame reset
// configuration required convergence from zero each time. The current board top keeps
// the estimate across frames through rst_dc, as described below.
//
// The original fixed K=6 (tau = 64 samples = 8 symbols) converges fine and was validated at
// BER=0 on a real self-OTA capture, but it is short enough to track the data: a run of
// identical symbols on one axis drags the estimate toward that run, and the sample at the
// END of the run loses the most. That is not hypothetical. On the two-board link it cost
// 66% of the decision margin at payload bit 189 -- the Q axis of symbol 106, the last of a
// four-symbol Q run -- making it the WEAKEST of all 256 payload decisions (margin 0.336 vs
// a 0.99 median) and the site of 37 of 40 observed single-bit errors. The offline model in
// dc_blocker_margin.py reproduces the whole live histogram: the three indices that ever
// failed live rank 1, 3 and 23 of 256 by predicted margin, in frequency order.
//
// The fix is NOT to gear from a short constant to a long one at a fixed sample count. That
// was tried and it regressed tb_qpsk_timing_recovery_retained, for a reason worth keeping:
// over a short window the modulation's own local imbalance IS the dominant term, so the
// acquisition window measures the wrong DC (that capture's first 192 samples average
// 79+44j while its true DC is 4.5+1.1j), and gearing down then FREEZES that error into a
// slowly-decaying offset across the whole frame. A fast wrong estimate is self-correcting;
// a slow wrong estimate is not.
//
// Instead the estimate uses a power-of-two approximation to a running average:
// K grows as floor(log2(n)) up to K_MAX, and the update weight is 1/2^K rather than 1/n.
// It is not the exact arithmetic mean (after inputs 120, 0, 0 the estimate is 30, not 40).
// The effective averaging window grows with acquisition; once K reaches K_MAX the block
// becomes a leaky integrator with tau = 2^K_MAX that can still follow a drifting LO.
//
// acc holds mean << K, so each time K increments the stored estimate is re-scaled by one
// left shift to represent the same mean. Miss that and the estimate halves at every step.
//
// Resetting every frame has its own cost (issue #66). At the preamble the running mean covers
// only a few hundred samples, and the differential preamble repeats one symbol, so the block
// subtracts part of the preamble; on two boards that cost frame locks and bits, and after a
// sudden 20 dB level drop the offset learned on the strong signal was most of the weak one.
// qpsk_zynq_ber_top therefore no longer resets this block per frame (DC_PERSIST = 1, through
// the chain's rst_dc) and uses K_MAX = 13: the estimate is kept from burst to burst and
// averages over several frames. Benches that drive the chain directly still reset it per run.

`timescale 1ns/1ps

module dc_blocker #(
    parameter integer W = 16,
    parameter integer K_MAX = 10     // final time constant ~2^K_MAX samples (128 symbols @ SPS=8)
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

localparam integer AW = W + K_MAX + 1;      // acc holds mean << K, K <= K_MAX
localparam integer KW = $clog2(K_MAX + 1);
localparam integer NW = K_MAX + 1;          // counts only up to 2^K_MAX, then freezes

reg signed [AW-1:0] acc_i;
reg signed [AW-1:0] acc_q;
reg [KW-1:0]        k;
reg [NW-1:0]        n_count;                // samples already averaged
reg [NW-1:0]        thresh;                 // 1, 3, 7, ... : n_count value at which K steps

// K steps when the sample count reaches the next power of two, approximating the
// reciprocal sample-count weight without a divider.
wire step = in_valid && (k < K_MAX) && (n_count == thresh);
wire [KW-1:0]        k_cur   = step ? (k + 1'b1) : k;
wire signed [AW-1:0] acc_i_c = step ? (acc_i <<< 1) : acc_i;   // re-scale for the new K
wire signed [AW-1:0] acc_q_c = step ? (acc_q <<< 1) : acc_q;

wire signed [AW-1:0] acc_i_sr = acc_i_c >>> k_cur;   // arithmetic shift = acc / 2^K
wire signed [AW-1:0] acc_q_sr = acc_q_c >>> k_cur;
wire signed [W-1:0]  dc_i = acc_i_sr[W-1:0];         // the mean fits in W bits
wire signed [W-1:0]  dc_q = acc_q_sr[W-1:0];

always @(posedge clk) begin
    if (rst) begin
        acc_i     <= {AW{1'b0}};
        acc_q     <= {AW{1'b0}};
        k         <= {KW{1'b0}};
        n_count   <= {NW{1'b0}};
        thresh    <= {{(NW-1){1'b0}}, 1'b1};
        out_valid <= 1'b0;
        out_i     <= {W{1'b0}};
        out_q     <= {W{1'b0}};
    end else begin
        out_valid <= in_valid;
        if (in_valid) begin
            // acc += in - (acc >>> K): an approximate running mean during acquisition,
            // then a fixed-weight leaky integrator at K_MAX. Operands are signed and so
            // sign-extend to the accumulator width.
            acc_i <= acc_i_c + in_i - dc_i;
            acc_q <= acc_q_c + in_q - dc_q;
            out_i <= enable ? (in_i - dc_i) : in_i;
            out_q <= enable ? (in_q - dc_q) : in_q;
            k     <= k_cur;
            if (step) begin
                thresh <= {thresh[NW-2:0], 1'b1};    // 1 -> 3 -> 7 -> ...
            end
            if (k < K_MAX) begin                     // freeze the counter once K is final
                n_count <= n_count + 1'b1;
            end
        end
    end
end

endmodule
