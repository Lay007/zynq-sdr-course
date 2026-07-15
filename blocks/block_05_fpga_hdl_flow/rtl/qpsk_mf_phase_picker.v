// Lab 5.13 - feedforward symbol-timing phase pick for a burst receiver.
//
// A matched filter peaks at the symbol centres. So the right sampling phase is simply the
// one carrying the most energy: accumulate |I|+|Q| separately for each of the SPS sample
// phases over a short window, and take the argmax. No loop, no acquisition time, nothing to
// pull in -- which is what a 140-symbol burst wants. A Gardner loop has to converge inside
// the preamble and, on these bursts, does not.
//
// The measurement needs signal, and the signal is the frame, so the frame would be half over
// before a phase existed. Hence the delay line: the stream is held for the length of the
// window, the phase is decided on the live samples, and only then is the DELAYED stream
// released, tapped so that its first released sample is a symbol centre. A downstream
// fixed-phase sampler with start_offset=0 therefore lands dead centre on every symbol, and
// the preamble is still intact.
//
// Why this matters: the single-board self-OTA link used to hand the receiver a frame that
// arrived at a different sub-symbol offset on every burst (a DAC-FIFO artefact, since fixed).
// Two boards with independent references will do worse -- the phase will drift WITHIN a
// frame, not merely between bursts -- and no amount of carrier-loop tuning touches that.
//
// Pass-through when `enable` is low, so the coherent fabric loopback stays bit-identical.

`timescale 1ns/1ps

module qpsk_mf_phase_picker #(
    parameter integer W = 16,
    parameter integer SPS = 8,
    // Energy window, in symbols. Long enough to average the modulation away (QPSK symbols
    // are constant modulus, but the RRC ramp and noise are not), short enough to finish well
    // inside the preamble.
    parameter integer WIN_SYMBOLS = 6,
    // Start the window when the burst is actually present, on the same |I|+|Q| test the
    // carrier loop's freeze gate uses. 0 = start on the first valid sample.
    parameter integer SIG_THRESH = 1000,
    // Fixed correction for the delay line's read latency (`locked` rises one sample after the
    // window closes, so the line has already shifted by the time the first sample is released)
    // and for the downstream sampler's own first-sample convention. MEASURED, not guessed:
    // sweeping it against two real captures at start_offset=0 gives BER 0 for TAP_TRIM 3, 4
    // and 5 on both, so 4 sits in the middle of the clean window with a symbol-eighth of
    // margin either side. With TAP_TRIM=0 the released stream starts half a symbol off.
    parameter integer TAP_TRIM = 4
) (
    input  wire                 clk,
    input  wire                 rst,
    input  wire                 enable,
    input  wire                 in_valid,
    input  wire signed [W-1:0]  in_i,
    input  wire signed [W-1:0]  in_q,
    output wire                 out_valid,
    output wire signed [W-1:0]  out_i,
    output wire signed [W-1:0]  out_q,
    output wire                 phase_locked,
    output wire [2:0]           phase          // the chosen sample phase, for observability
);

localparam integer WIN_SAMPLES = WIN_SYMBOLS * SPS;
// One extra symbol of slack so the tap can reach back a whole symbol period.
localparam integer DEPTH = WIN_SAMPLES + SPS + 1;
// Each phase receives WIN_SYMBOLS magnitudes; 20 bits cover the worst-case six-sample
// accumulation for 16-bit I/Q with margin, and keep the 250 MHz add/compare paths short.
localparam integer ACC_W = 20;

integer k;

// ---------------------------------------------------------------------------
// Delay line. Written on in_valid, so its index is in samples, not clocks.
// ---------------------------------------------------------------------------
reg signed [W-1:0] dl_i [0:DEPTH-1];
reg signed [W-1:0] dl_q [0:DEPTH-1];

always @(posedge clk) begin
    if (in_valid) begin
        dl_i[0] <= in_i;
        dl_q[0] <= in_q;
        for (k = 1; k < DEPTH; k = k + 1) begin
            dl_i[k] <= dl_i[k-1];
            dl_q[k] <= dl_q[k-1];
        end
    end
end

// ---------------------------------------------------------------------------
// Signal gate and per-phase energy accumulators.
// ---------------------------------------------------------------------------
wire [W-1:0] abs_i = in_i[W-1] ? (~in_i + 1'b1) : in_i;
wire [W-1:0] abs_q = in_q[W-1] ? (~in_q + 1'b1) : in_q;
wire [W:0]   mag   = {1'b0, abs_i} + {1'b0, abs_q};
wire sig_present = (SIG_THRESH == 0) || (mag >= SIG_THRESH[W:0]);

reg [2:0]  ph_cnt = 3'd0;                  // sample phase of the newest sample
reg [15:0] win_cnt = 16'd0;
reg        measuring = 1'b0;
reg        locked = 1'b0;
reg [2:0]  best_ph = 3'd0;
reg [ACC_W-1:0] acc [0:7];

// The last symbol visits all eight phases in order. Compare each phase when its final
// contribution arrives instead of building an eight-way combinational argmax. This leaves
// one phase comparison at a time on the 250 MHz path, rather than a seven-comparator chain.
reg [2:0] final_best_ph = 3'd0;
reg [ACC_W-1:0] final_best_acc = {ACC_W{1'b0}};
wire [ACC_W-1:0] phase_sum =
    acc[ph_cnt] + {{(ACC_W-(W+1)){1'b0}}, mag};
// Compare the five contributions already stored when the sixth (scheduling) symbol visits
// the phase. The sixth contribution is still accumulated, but keeping its adder off the
// argmax path is valuable at 250 MHz and five full symbols are ample for the energy pick.
wire current_phase_wins = acc[ph_cnt] > final_best_acc;
wire [2:0] winning_phase = current_phase_wins ? ph_cnt : final_best_ph;

// Tap: the first released sample must be a symbol centre. At the instant we lock, the newest
// sample has phase ph_cnt, so dl[k] carries phase (ph_cnt - k) mod SPS. Reach back to the
// most recent centre, then add the whole window so nothing measured is thrown away.
// WIN_SAMPLES is a multiple of SPS, so it does not disturb the phase arithmetic.
reg [2:0] tap_sel = 3'd0;
wire [2:0] back = (ph_cnt - winning_phase) & 3'd7;

always @(posedge clk) begin
    if (rst) begin
        ph_cnt    <= 3'd0;
        win_cnt   <= 16'd0;
        measuring <= 1'b0;
        locked    <= 1'b0;
        best_ph   <= 3'd0;
        tap_sel   <= 3'd0;
        final_best_ph  <= 3'd0;
        final_best_acc <= {ACC_W{1'b0}};
        for (k = 0; k < 8; k = k + 1) acc[k] <= {ACC_W{1'b0}};
    end else if (in_valid) begin
        ph_cnt <= ph_cnt + 3'd1;
        if (!locked) begin
            if (!measuring) begin
                // Anchor the phase counter to the first signal-bearing sample so the window
                // and the released stream share one origin.
                if (sig_present) begin
                    measuring <= 1'b1;
                    ph_cnt    <= 3'd1;
                    win_cnt   <= 16'd1;
                    for (k = 0; k < 8; k = k + 1) acc[k] <= {ACC_W{1'b0}};
                    acc[0] <= {{(ACC_W-(W+1)){1'b0}}, mag};
                    final_best_ph  <= 3'd0;
                    final_best_acc <= {ACC_W{1'b0}};
                end
            end else begin
                acc[ph_cnt] <= phase_sum;
                if (win_cnt >= (WIN_SAMPLES - SPS)) begin
                    if (current_phase_wins) begin
                        final_best_acc <= acc[ph_cnt];
                        final_best_ph  <= ph_cnt;
                    end
                end
                if (win_cnt == WIN_SAMPLES[15:0] - 16'd1) begin
                    locked <= 1'b1;
                    best_ph <= winning_phase;
                    // dl[back] is the newest centre; the window sits behind it.
                    tap_sel <= (back + TAP_TRIM[2:0]) & 3'd7;
                end else begin
                    win_cnt <= win_cnt + 16'd1;
                end
            end
        end
    end
end

// ---------------------------------------------------------------------------
// Output. Bypassed entirely when disabled, so the clean paths are untouched.
// ---------------------------------------------------------------------------
// Only eight locations are reachable. Keeping the selector three bits wide prevents Vivado
// from constructing a 57-way mux for a broadly sized dynamic array index.
reg signed [W-1:0] tapped_i;
reg signed [W-1:0] tapped_q;
always @(*) begin
    case (tap_sel)
        3'd0: begin tapped_i = dl_i[WIN_SAMPLES + 0]; tapped_q = dl_q[WIN_SAMPLES + 0]; end
        3'd1: begin tapped_i = dl_i[WIN_SAMPLES + 1]; tapped_q = dl_q[WIN_SAMPLES + 1]; end
        3'd2: begin tapped_i = dl_i[WIN_SAMPLES + 2]; tapped_q = dl_q[WIN_SAMPLES + 2]; end
        3'd3: begin tapped_i = dl_i[WIN_SAMPLES + 3]; tapped_q = dl_q[WIN_SAMPLES + 3]; end
        3'd4: begin tapped_i = dl_i[WIN_SAMPLES + 4]; tapped_q = dl_q[WIN_SAMPLES + 4]; end
        3'd5: begin tapped_i = dl_i[WIN_SAMPLES + 5]; tapped_q = dl_q[WIN_SAMPLES + 5]; end
        3'd6: begin tapped_i = dl_i[WIN_SAMPLES + 6]; tapped_q = dl_q[WIN_SAMPLES + 6]; end
        default: begin tapped_i = dl_i[WIN_SAMPLES + 7]; tapped_q = dl_q[WIN_SAMPLES + 7]; end
    endcase
end

assign out_valid    = enable ? (in_valid && locked) : in_valid;
assign out_i        = enable ? tapped_i : in_i;
assign out_q        = enable ? tapped_q : in_q;
assign phase_locked = locked;
assign phase        = best_ph;

endmodule
