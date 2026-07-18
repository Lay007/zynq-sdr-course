// Lab 5.9b - QPSK RX dibit-recovery chain
//
// Reuses the shared complex-I/Q matched filter and fixed-phase symbol timing
// sampler (same blocks as the BPSK RX), then makes a Gray QPSK hard decision:
//   matched filter -> fixed-phase sampler -> qpsk_hard_decision -> dibit.

`timescale 1ns/1ps

module qpsk_rx_bit_recovery_chain #(
    parameter integer W = 16,
    parameter integer SPS = 8,
    parameter integer INDEX_W = 16,
    parameter integer DC_BLOCK_K = 6,
    parameter integer COSTAS_KP_LOG_ACQ = 8,     // pull-in must finish inside the 12-symbol preamble
    parameter integer COSTAS_KP_LOG_TRACK = 6,   // ... then track quietly, or the loop slips mid-frame
    parameter integer COSTAS_ACQ_SYMBOLS = 32,   // counted from the freeze gate, which opens
                                                  // ~16 symbols before the frame-sync locks
    parameter integer COSTAS_KI_LOG = 1,
    parameter integer COSTAS_SIG_THRESH = 1000,  // freeze-gate: hold the loop while |I|+|Q| < this
                                                  // (works 600..1400 on real self-OTA; noise <600, signal >1400)
    parameter integer COARSE_WIN_SYMBOLS = 64,    // 4th-power measurement window (also the derotate delay)
    parameter integer COARSE_SQ_SHIFT = 11,       // per-square right shift, ~log2(|MF symbol|) ~ 2000 -> 11
    parameter COEF_FILE = "blocks/block_05_fpga_hdl_flow/rtl/bpsk_rrc_tx_fir_taps.mem"
) (
    input  wire                     clk,
    input  wire                     rst,
    // Reset for the carrier loop's phase/frequency accumulators only. Tie to `rst` for the
    // usual "start every frame from zero phase"; hold it low across frames to keep the
    // acquired carrier phase (see qpsk_costas.rst_phase).
    input  wire                     rst_carrier,
    input  wire                     dc_block_en,   // 1 = subtract LO-leakage DC (OTA); 0 = passthrough
    input  wire                     costas_en,     // 1 = carrier tracking (OTA); 0 = passthrough
    input  wire                     coarse_cfo_en, // 1 = strip bulk inter-board CFO before Costas; 0 = passthrough
    input  wire                     phase_pick_en, // 1 = feedforward 8-phase burst timing pick
    input  wire                     in_valid,
    input  wire signed [W-1:0]      in_i,
    input  wire signed [W-1:0]      in_q,
    input  wire [INDEX_W-1:0]       start_offset,
    input  wire [INDEX_W-1:0]       symbol_count,
    output wire                     out_valid,
    output wire [1:0]               out_dibit,
    output wire                     debug_symbol_valid,
    output wire signed [W-1:0]      debug_symbol_i,
    output wire signed [W-1:0]      debug_symbol_q,
    // Observability: the coarse-CFO estimate for the current burst (per-symbol phase increment,
    // full scale 2^24 = 2*pi) and its ready strobe. Leave unconnected if not needed.
    output wire                     cfo_ready,
    output wire signed [23:0]       cfo_omega
);

// DC blocker on the RX sample front: removes the AD9361 LO-leakage DC offset that
// dominates a real over-the-air capture. Passthrough when dc_block_en=0 keeps the
// clean fabric-loopback path effectively unchanged (DC-free input -> ~0 subtracted).
wire dc_valid;
wire signed [W-1:0] dc_i;
wire signed [W-1:0] dc_q;
dc_blocker #(
    .W(W),
    .K(DC_BLOCK_K)
) dc_blocker_i (
    .clk(clk),
    .rst(rst),
    .enable(dc_block_en),
    .in_valid(in_valid),
    .in_i(in_i),
    .in_q(in_q),
    .out_valid(dc_valid),
    .out_i(dc_i),
    .out_q(dc_q)
);

wire mf_valid;
wire signed [W-1:0] mf_i;
wire signed [W-1:0] mf_q;
wire picked_valid;
wire signed [W-1:0] picked_i;
wire signed [W-1:0] picked_q;
wire sym_valid;
wire signed [W-1:0] sym_i;
wire signed [W-1:0] sym_q;

bpsk_rrc_rx_fir #(
    .COEF_FILE(COEF_FILE)
) matched_filter_i (
    .clk(clk),
    .rst(rst),
    .in_valid(dc_valid),
    .in_i(dc_i),
    .in_q(dc_q),
    .out_valid(mf_valid),
    .out_i(mf_i),
    .out_q(mf_q)
);

// A burst can arrive at any of the SPS sub-symbol phases. Measure matched-filter
// energy over a short window, delay the intact preamble, and release the stream
// on the strongest phase. Bypass keeps all coherent/internal paths unchanged.
qpsk_mf_phase_picker #(
    .W(W),
    .SPS(SPS),
    .SIG_THRESH(COSTAS_SIG_THRESH)
) phase_picker_i (
    .clk(clk),
    .rst(rst),
    .enable(phase_pick_en),
    .in_valid(mf_valid),
    .in_i(mf_i),
    .in_q(mf_q),
    .out_valid(picked_valid),
    .out_i(picked_i),
    .out_q(picked_q),
    .phase_locked(),
    .phase()
);

bpsk_symbol_timing_sampler #(
    .W(W),
    .SPS(SPS),
    .INDEX_W(INDEX_W)
) timing_i (
    .clk(clk),
    .rst(rst),
    .in_valid(picked_valid),
    .in_i(picked_i),
    .in_q(picked_q),
    .start_offset(start_offset),
    .symbol_count(symbol_count),
    .out_valid(sym_valid),
    .out_i(sym_i),
    .out_q(sym_q)
);

// Feedforward coarse-CFO removal, ahead of the Costas loop. Two independent-oscillator boards
// sit tens of kHz apart -- far outside the Costas pull-in (a few hundred Hz), so the loop alone
// never acquires. This 4th-power estimator strips the QPSK modulation, measures the per-symbol
// phase increment over COARSE_WIN_SYMBOLS, and derotates the buffered burst (delayed by the
// window) so Costas only has to close a small residual. Its output is registered (one clock in
// BOTH modes, passthrough included), which keeps the long derotate off the downstream Costas
// enable gate so timing closes; the coherent fabric loopback still decodes at BER 0 (the uniform
// one-clock delay is below the sampler phase choice, so start_offset is unchanged).
wire cfo_out_valid;
wire signed [W-1:0] cfo_out_i;
wire signed [W-1:0] cfo_out_q;
qpsk_coarse_cfo #(
    .W(W),
    .WIN_SYMBOLS(COARSE_WIN_SYMBOLS),
    .SQ_SHIFT(COARSE_SQ_SHIFT),
    .SIG_THRESH(COSTAS_SIG_THRESH)
) coarse_cfo_i (
    .clk(clk),
    .rst(rst),
    .enable(coarse_cfo_en),
    .in_valid(sym_valid),
    .in_i(sym_i),
    .in_q(sym_q),
    .out_valid(cfo_out_valid),
    .out_i(cfo_out_i),
    .out_q(cfo_out_q),
    .cfo_ready(cfo_ready),
    .cfo_omega(cfo_omega)
);

// Carrier-recovery Costas loop tracks the per-burst carrier phase of a real OTA link
// (the fixed-phase sampler alone floors at ~44%). Passthrough when costas_en=0 keeps
// the coherent fabric loopback bit-identical. The residual 90-degree QPSK ambiguity is
// resolved downstream by the preamble frame-sync in the BER counter.
wire cos_valid;
wire signed [W-1:0] cos_i;
wire signed [W-1:0] cos_q;
qpsk_costas #(
    .W(W),
    .KP_LOG_ACQ(COSTAS_KP_LOG_ACQ),
    .KP_LOG_TRACK(COSTAS_KP_LOG_TRACK),
    .ACQ_SYMBOLS(COSTAS_ACQ_SYMBOLS),
    .KI_LOG(COSTAS_KI_LOG),
    .SIG_THRESH(COSTAS_SIG_THRESH)
) costas_i (
    .clk(clk),
    .rst(rst),
    .rst_phase(rst_carrier),
    .enable(costas_en),
    .in_valid(cfo_out_valid),
    .in_i(cfo_out_i),
    .in_q(cfo_out_q),
    .out_valid(cos_valid),
    .out_i(cos_i),
    .out_q(cos_q)
);

// Signal-present gate on the decision. A real burst begins with hundreds of samples
// of pre-frame NOISE (the AD9361 round-trip latency), whose hard decisions are random
// bits. Fed to the frame-sync correlator they occasionally match the preamble within
// LOCK_ERR_TOL and false-lock the frame ahead of the real one (~5% of bursts, seen on
// hardware as a "locked" frame with ~50% errors). Suppressing the decision until the
// burst actually arrives removes that exposure. The gate LATCHES open on the first
// signal-present symbol, so a mid-frame dip can never drop a symbol and shift the bit
// alignment. Only active with costas_en (the OTA path) so the coherent fabric loopback
// stays bit-identical; COSTAS_SIG_THRESH=0 disables it entirely.
wire [W-1:0] abs_ci = cos_i[W-1] ? (~cos_i + 1'b1) : cos_i;
wire [W-1:0] abs_cq = cos_q[W-1] ? (~cos_q + 1'b1) : cos_q;
wire sig_now = (COSTAS_SIG_THRESH == 0) ||
               (({1'b0, abs_ci} + {1'b0, abs_cq}) >= COSTAS_SIG_THRESH[W:0]);

reg sig_seen = 1'b0;
always @(posedge clk) begin
    if (rst) sig_seen <= 1'b0;
    else if (cos_valid && sig_now) sig_seen <= 1'b1;
end

wire dec_valid = cos_valid && (!costas_en || sig_now || sig_seen);

qpsk_hard_decision decision_i (
    .clk(clk),
    .rst(rst),
    .in_valid(dec_valid),
    .in_i(cos_i),
    .in_q(cos_q),
    .out_valid(out_valid),
    .out_dibit(out_dibit)
);

assign debug_symbol_valid = cos_valid;
assign debug_symbol_i = cos_i;
assign debug_symbol_q = cos_q;

endmodule
