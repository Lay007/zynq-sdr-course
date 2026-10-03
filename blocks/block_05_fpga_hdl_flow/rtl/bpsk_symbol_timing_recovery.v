// Lab 5.8b - BPSK Gardner symbol timing recovery
//
// Drop-in alternative to bpsk_symbol_timing_sampler: instead of decimating the
// matched-filter stream at a fixed phase (which cannot follow a samples-per-symbol
// error / timing drift over a burst), this closes a digital timing-recovery loop:
//
//   * decrementing modulo-1 NCO produces 2 strobes/symbol (on-time + mid-symbol),
//   * a linear interpolator evaluates the matched-filter stream at each strobe
//     (mu ~= nco<<2, exact for the nominal step w = 2/SPS),
//   * a sign-Gardner timing-error detector  e = sgn(y_mid)*sgn(y_on[k]-y_on[k-1])
//     (amplitude-independent -> stable across RX gain / signal level),
//   * a proportional-integral loop filter steers the NCO step w.
//
// The integer datapath is a bit-exact port of a validated fixed-point model:
// e in {-1,0,+1}, so the loop uses constant +/-K steps only (no multipliers in the
// loop). The single interpolator multiply is the only product. Output is the
// on-time complex symbol; the downstream decision_mode + hard decision are
// unchanged. start_offset positions the first on-time strobe, then the loop tracks.
//
// PIPELINED selects how the loop is scheduled; the output symbols are the same,
// value for value, in both modes (tb_bpsk_symbol_timing_recovery_equivalence):
//   0: teaching form. At a strobe, NCO -> mu -> interpolation multiply -> add ->
//      saturate -> timing error -> loop filter -> clamp -> new step, all in one
//      clock (about 52 MHz on xc7z020-2).
//   1: timing-closed form (about 103 MHz). The strobe clock only captures the interpolation
//      operands; the product is registered in the next clock; the clock after
//      that forms the symbol, the timing error and the loop update. Two ideas
//      make this exact:
//      * the new step w is only needed at the next strobe, which is at least
//        three samples away when 3*W_MAX <= 1.0 (checked below). The samples in
//        between only step the NCO by w, so the update rewrites the NCO as
//        "NCO after the strobe - k*w_new", k = samples consumed since (0..2);
//      * lookahead: e has only three values, so the three possible loop-filter
//        results (step, integrator, NCO for each k) are computed and registered
//        at the strobe, and e just selects one.
//      The output symbol leaves two clocks later than in mode 0.

`timescale 1ns/1ps

module bpsk_symbol_timing_recovery #(
    parameter integer W = 16,
    parameter integer SPS = 8,
    parameter integer INDEX_W = 16,
    parameter integer NCO_W = 16,
    parameter integer INTEG_W = 24,
    parameter integer PIPELINED = 1
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

localparam integer NCO_ONE   = (1 <<< NCO_W);          // 1.0 in Q.16  (65536)
localparam integer W_NOMINAL = ((2 <<< NCO_W) / SPS);  // 2 strobes/symbol (16384 @SPS=8)
localparam integer K1_TERM   = (NCO_ONE / 256);        // proportional |step|  (256)
localparam integer K2_TERM   = (NCO_ONE / 4096);       // integral |increment| (16)
localparam integer W_MIN     = W_NOMINAL - 2048;
localparam integer W_MAX     = W_NOMINAL + 2048;
localparam signed [W-1:0] SAT_MAX = {1'b0, {(W-1){1'b1}}};   //  32767
localparam signed [W-1:0] SAT_MIN = {1'b1, {(W-1){1'b0}}};   // -32768

generate
    if ((PIPELINED != 0) && (3 * W_MAX > NCO_ONE)) begin : g_bad_sps
        // A strobe could then fall within two samples of the previous one,
        // before the delayed loop update. Use PIPELINED=0 for this SPS.
        initial begin
            $display("ERROR: bpsk_symbol_timing_recovery PIPELINED=1 needs 3*W_MAX <= 1.0 (SPS=%0d)", SPS);
            $finish;
        end
    end
endgenerate

reg [INDEX_W-1:0]        in_count;
reg                      started;
reg signed [31:0]        nco;          // Q.16, kept in [0,1)
reg signed [31:0]        w_step;       // Q.16 NCO step
reg signed [INTEG_W-1:0] integ;        // integral accumulator (Q.16)
reg signed [W-1:0]       x_prev_i;
reg signed [W-1:0]       x_prev_q;
reg signed [W-1:0]       y_on_prev_i;
reg signed [W-1:0]       y_mid_i;
reg                      parity;       // 0 = on-time strobe, 1 = mid-symbol strobe
reg [INDEX_W-1:0]        emitted;

// mu ~= nco/w ~= nco<<2 for w ~= 2/SPS; saturate just below 1.0
wire signed [31:0] mu_raw = nco <<< 2;
wire signed [31:0] mu = (mu_raw >= NCO_ONE) ? (NCO_ONE - 1) : mu_raw;

// Interpolation operands. di is W+1 bits and mu NCO_W+1 bits (both signed), so
// one DSP48E1 holds each product; the values equal the 32-bit original.
wire signed [W:0]     di_now = $signed(in_i) - $signed(x_prev_i);
wire signed [W:0]     dq_now = $signed(in_q) - $signed(x_prev_q);
wire signed [NCO_W:0] mu_now = mu[NCO_W:0];

// A sample is consumed by the running loop (the NCO steps) in this clock.
wire consume = in_valid && started && (emitted < symbol_count);
wire strobe  = consume && (nco < w_step);

// ---------------------------------------------------------------------------
// PIPELINED=1 state
// ---------------------------------------------------------------------------
// Stage 1 (strobe clock): operands and lookahead candidates.
reg                      s1_valid;
reg                      s1_on_time;
reg signed [W-1:0]       s1_x_prev_i;
reg signed [W-1:0]       s1_x_prev_q;
reg signed [W:0]         s1_di;
reg signed [W:0]         s1_dq;
reg signed [NCO_W:0]     s1_mu;
// Stage 2: registered products.
reg                      s2_valid;
reg                      s2_on_time;
reg signed [W-1:0]       s2_x_prev_i;
reg signed [W-1:0]       s2_x_prev_q;
reg signed [W+NCO_W+1:0] s2_mu_di;
reg signed [W+NCO_W+1:0] s2_mu_dq;
reg                      s2_consumed;  // a sample was consumed in the clock after the strobe
// Lookahead candidates for e = -1 (m), 0 (z), +1 (p), valid until the update.
reg signed [INTEG_W-1:0] c_integ_m, c_integ_z, c_integ_p;
reg signed [31:0]        c_w_m, c_w_z, c_w_p;
reg signed [31:0]        c_nco0;                       // NCO right after the strobe
reg signed [31:0]        c_nco1_m, c_nco1_z, c_nco1_p; // ... minus one new step
reg signed [31:0]        c_nco2_m, c_nco2_z, c_nco2_p; // ... minus two new steps

function automatic signed [31:0] clamp_step;
    input signed [31:0] value;
    begin
        clamp_step = (value < W_MIN) ? W_MIN : (value > W_MAX) ? W_MAX : value;
    end
endfunction

// Candidate values from the registers at the strobe (not on the symbol path).
wire signed [INTEG_W-1:0] integ_m = integ - K2_TERM;
wire signed [INTEG_W-1:0] integ_p = integ + K2_TERM;
wire signed [31:0] w_cand_m = clamp_step(W_NOMINAL - K1_TERM + integ_m);
wire signed [31:0] w_cand_z = clamp_step(W_NOMINAL + integ);
wire signed [31:0] w_cand_p = clamp_step(W_NOMINAL + K1_TERM + integ_p);
wire signed [31:0] nco_after_strobe = nco - w_step + NCO_ONE;

// ---------------------------------------------------------------------------
// Symbol, timing error and loop filter
// ---------------------------------------------------------------------------
wire signed [W+NCO_W+1:0] mu_di = (PIPELINED != 0) ? s2_mu_di : di_now * mu_now;
wire signed [W+NCO_W+1:0] mu_dq = (PIPELINED != 0) ? s2_mu_dq : dq_now * mu_now;
wire signed [W-1:0]       xp_i  = (PIPELINED != 0) ? s2_x_prev_i : x_prev_i;
wire signed [W-1:0]       xp_q  = (PIPELINED != 0) ? s2_x_prev_q : x_prev_q;

// linear interpolation: y = x_prev + ((cur - x_prev) * mu) >>> NCO_W   (mu in [0,1))
wire signed [31:0] y_i32 = $signed(xp_i) + (mu_di >>> NCO_W);
wire signed [31:0] y_q32 = $signed(xp_q) + (mu_dq >>> NCO_W);
wire signed [W-1:0] y_i = (y_i32 > SAT_MAX) ? SAT_MAX : (y_i32 < SAT_MIN) ? SAT_MIN : y_i32[W-1:0];
wire signed [W-1:0] y_q = (y_q32 > SAT_MAX) ? SAT_MAX : (y_q32 < SAT_MIN) ? SAT_MIN : y_q32[W-1:0];

// sign-Gardner timing error  e = sgn(y_mid) * sgn(y_on - y_on_prev)
wire signed [31:0] dy = $signed(y_i) - $signed(y_on_prev_i);
wire signed [1:0]  sgn_mid = (y_mid_i > 0) ? 2'sd1 : (y_mid_i < 0) ? -2'sd1 : 2'sd0;
wire signed [1:0]  sgn_dy  = (dy      > 0) ? 2'sd1 : (dy      < 0) ? -2'sd1 : 2'sd0;
wire signed [2:0]  e_ted   = sgn_mid * sgn_dy;   // {-1,0,+1}

// Loop filter as written in the model (PIPELINED=0).
wire signed [INTEG_W-1:0] integ_next = integ + K2_TERM * e_ted;
wire signed [31:0] w_unclamped = W_NOMINAL + (K1_TERM * e_ted) + integ_next;
wire signed [31:0] w_clamped   = (w_unclamped < W_MIN) ? W_MIN :
                                 (w_unclamped > W_MAX) ? W_MAX : w_unclamped;

// PIPELINED=1: e selects a registered candidate; k = samples consumed since the
// strobe, counting this clock.
wire [1:0] k_steps = {1'b0, s2_consumed} + {1'b0, consume};
wire signed [INTEG_W-1:0] integ_sel = (e_ted > 0) ? c_integ_p : (e_ted < 0) ? c_integ_m : c_integ_z;
wire signed [31:0]        w_sel     = (e_ted > 0) ? c_w_p     : (e_ted < 0) ? c_w_m     : c_w_z;
wire signed [31:0]        nco1_sel  = (e_ted > 0) ? c_nco1_p  : (e_ted < 0) ? c_nco1_m  : c_nco1_z;
wire signed [31:0]        nco2_sel  = (e_ted > 0) ? c_nco2_p  : (e_ted < 0) ? c_nco2_m  : c_nco2_z;
wire signed [31:0]        nco_sel   = (k_steps == 2'd0) ? c_nco0 :
                                      (k_steps == 2'd1) ? nco1_sel : nco2_sel;

always @(posedge clk) begin
    if (rst) begin
        in_count    <= {INDEX_W{1'b0}};
        started     <= 1'b0;
        nco         <= 32'sd0;
        w_step      <= W_NOMINAL;
        integ       <= {INTEG_W{1'b0}};
        x_prev_i    <= {W{1'b0}};
        x_prev_q    <= {W{1'b0}};
        y_on_prev_i <= {W{1'b0}};
        y_mid_i     <= {W{1'b0}};
        parity      <= 1'b0;
        emitted     <= {INDEX_W{1'b0}};
        out_valid   <= 1'b0;
        out_i       <= {W{1'b0}};
        out_q       <= {W{1'b0}};
        s1_valid    <= 1'b0;
        s1_on_time  <= 1'b0;
        s1_x_prev_i <= {W{1'b0}};
        s1_x_prev_q <= {W{1'b0}};
        s1_di       <= {(W+1){1'b0}};
        s1_dq       <= {(W+1){1'b0}};
        s1_mu       <= {(NCO_W+1){1'b0}};
        s2_valid    <= 1'b0;
        s2_on_time  <= 1'b0;
        s2_x_prev_i <= {W{1'b0}};
        s2_x_prev_q <= {W{1'b0}};
        s2_mu_di    <= {(W+NCO_W+2){1'b0}};
        s2_mu_dq    <= {(W+NCO_W+2){1'b0}};
        s2_consumed <= 1'b0;
        c_integ_m   <= {INTEG_W{1'b0}};
        c_integ_z   <= {INTEG_W{1'b0}};
        c_integ_p   <= {INTEG_W{1'b0}};
        c_w_m       <= W_NOMINAL;
        c_w_z       <= W_NOMINAL;
        c_w_p       <= W_NOMINAL;
        c_nco0      <= 32'sd0;
        c_nco1_m    <= 32'sd0;
        c_nco1_z    <= 32'sd0;
        c_nco1_p    <= 32'sd0;
        c_nco2_m    <= 32'sd0;
        c_nco2_z    <= 32'sd0;
        c_nco2_p    <= 32'sd0;
    end else begin
        out_valid <= 1'b0;
        out_i     <= {W{1'b0}};
        out_q     <= {W{1'b0}};
        s1_valid  <= 1'b0;
        s2_valid  <= 1'b0;

        if (in_valid) begin
            if (!started) begin
                if (in_count == start_offset) begin
                    // Transition: force the first (on-time) strobe on this sample.
                    started     <= 1'b1;
                    parity      <= 1'b1;            // next strobe is mid-symbol
                    y_on_prev_i <= x_prev_i;        // mu=0 -> y = x_prev
                    out_valid   <= 1'b1;
                    out_i       <= x_prev_i;
                    out_q       <= x_prev_q;
                    emitted     <= {{(INDEX_W-1){1'b0}}, 1'b1};
                    nco         <= (NCO_ONE - w_step);   // nco - w + 1 with nco = 0
                end else begin
                    in_count <= in_count + 1'b1;
                end
                x_prev_i <= in_i;
                x_prev_q <= in_q;
            end else if (emitted < symbol_count) begin
                if (strobe) begin
                    if (PIPELINED != 0) begin
                        // Capture operands and the loop-filter candidates; the
                        // symbol and the loop update follow two clocks later.
                        s1_valid    <= 1'b1;
                        s1_on_time  <= (parity == 1'b0);
                        s1_x_prev_i <= x_prev_i;
                        s1_x_prev_q <= x_prev_q;
                        s1_di       <= di_now;
                        s1_dq       <= dq_now;
                        s1_mu       <= mu_now;
                        c_integ_m   <= integ_m;
                        c_integ_z   <= integ;
                        c_integ_p   <= integ_p;
                        c_w_m       <= w_cand_m;
                        c_w_z       <= w_cand_z;
                        c_w_p       <= w_cand_p;
                        c_nco0      <= nco_after_strobe;
                        c_nco1_m    <= nco_after_strobe - w_cand_m;
                        c_nco1_z    <= nco_after_strobe - w_cand_z;
                        c_nco1_p    <= nco_after_strobe - w_cand_p;
                        c_nco2_m    <= nco_after_strobe - (w_cand_m <<< 1);
                        c_nco2_z    <= nco_after_strobe - (w_cand_z <<< 1);
                        c_nco2_p    <= nco_after_strobe - (w_cand_p <<< 1);
                        if (parity == 1'b0)
                            emitted <= emitted + 1'b1;
                    end else if (parity == 1'b0) begin
                        // on-time symbol: run TED + loop filter, emit
                        integ       <= integ_next;
                        w_step      <= w_clamped;
                        y_on_prev_i <= y_i;
                        out_valid   <= 1'b1;
                        out_i       <= y_i;
                        out_q       <= y_q;
                        emitted     <= emitted + 1'b1;
                    end else begin
                        // mid-symbol strobe: store for the next Gardner error
                        y_mid_i <= y_i;
                    end
                    parity <= ~parity;
                    nco    <= nco_after_strobe;
                end else begin
                    nco <= nco - w_step;
                end
                x_prev_i <= in_i;
                x_prev_q <= in_q;
            end
        end

        if (PIPELINED != 0) begin
            // Stage 2: registered interpolation products.
            s2_valid    <= s1_valid;
            s2_on_time  <= s1_on_time;
            s2_x_prev_i <= s1_x_prev_i;
            s2_x_prev_q <= s1_x_prev_q;
            s2_mu_di    <= s1_di * s1_mu;
            s2_mu_dq    <= s1_dq * s1_mu;
            s2_consumed <= consume;

            // Stage 3: symbol, timing error and loop update. No strobe can occur
            // in this clock or the one before, so these writes do not collide
            // with the per-sample logic above except for the NCO, which is
            // rewritten from the candidates here (last assignment wins).
            if (s2_valid) begin
                if (s2_on_time) begin
                    integ       <= integ_sel;
                    w_step      <= w_sel;
                    nco         <= nco_sel;
                    y_on_prev_i <= y_i;
                    out_valid   <= 1'b1;
                    out_i       <= y_i;
                    out_q       <= y_q;
                end else begin
                    y_mid_i <= y_i;
                end
            end
        end
    end
end

endmodule
