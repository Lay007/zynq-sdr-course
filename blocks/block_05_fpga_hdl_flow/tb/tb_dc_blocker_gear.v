// Lab 11.41 - the DC blocker must remove DC without following the data.
//
// A fixed short time constant cannot do both, and the two-board link proved it: K=6 tracked the
// modulation well enough to strip 66% of the decision margin at payload bit 189, the last symbol of
// a four-symbol Q run, which made it the weakest of 256 payload decisions and the site of 74 of 82
// observed single-bit errors. dc_blocker now averages every sample since reset (K grows as
// floor(log2 n)) before settling into a leak at tau = 2^K_MAX.
//
// The bench carries a behavioural twin of the ORIGINAL fixed-K algorithm and holds the DUT against
// it, so the comparison is with the code that actually shipped rather than with an ideal:
//   1. DC REMOVAL     - the injected offset must still go, or the fix trades one defect for a worse
//                       one (the LO leakage is comparable to the symbol amplitude).
//   2. DATA TRACKING  - against a square wave whose half period is one original time constant --
//                       the worst case, and what a run of identical symbols looks like on one axis
//                       -- the DUT must follow the data far less than the original did.
//   3. EARLY ESTIMATE - the running average must beat the original EARLY too, not just in steady
//                       state. A short window measures the modulation rather than the DC, and
//                       gearing down from one froze that error into the frame; that regression is
//                       what this check exists to catch if anyone reintroduces it.
//
// Checking exit status alone would pass all three while measuring nothing, so every check compares
// numbers and prints them.

`timescale 1ns/1ps

module tb_dc_blocker_gear;

localparam integer W = 16;
localparam integer K_LEGACY = 6;         // the original fixed time constant
localparam integer K_MAX = 10;
localparam integer RUN = 32;             // samples per half period = 4 symbols @ SPS=8
localparam integer NS = 40000;           // >> 3*2^K_MAX, so the slow loop fully converges
localparam integer SETTLE = 20000;
localparam integer EARLY = 1120;         // one 140-symbol frame: where the retained capture failed

localparam signed [W-1:0] DC_I = 16'sd5000;   // LO leakage, comparable to the symbol amplitude
localparam signed [W-1:0] DC_Q = -16'sd3000;
localparam signed [W-1:0] AMP  = 16'sd6000;   // modulation amplitude on Q

reg clk = 1'b0;
reg rst = 1'b1;
reg in_valid = 1'b0;
reg signed [W-1:0] in_i = 0;
reg signed [W-1:0] in_q = 0;

always #5 clk = ~clk;

wire dv;
wire signed [W-1:0] d_i, d_q;
dc_blocker #(.W(W), .K_MAX(K_MAX)) dut (
    .clk(clk), .rst(rst), .enable(1'b1), .in_valid(in_valid), .in_i(in_i), .in_q(in_q),
    .out_valid(dv), .out_i(d_i), .out_q(d_q)
);

// --- behavioural twin of the ORIGINAL fixed-K module ------------------------------------------
reg signed [W+K_LEGACY:0] ref_acc_i = 0;
reg signed [W+K_LEGACY:0] ref_acc_q = 0;
reg signed [W-1:0] ref_i = 0;
reg signed [W-1:0] ref_q = 0;
wire signed [W+K_LEGACY:0] ref_sr_i = ref_acc_i >>> K_LEGACY;
wire signed [W+K_LEGACY:0] ref_sr_q = ref_acc_q >>> K_LEGACY;
wire signed [W-1:0] ref_dc_i = ref_sr_i[W-1:0];
wire signed [W-1:0] ref_dc_q = ref_sr_q[W-1:0];

always @(posedge clk) begin
    if (rst) begin
        ref_acc_i <= 0; ref_acc_q <= 0; ref_i <= 0; ref_q <= 0;
    end else if (in_valid) begin
        ref_i     <= in_i - ref_dc_i;
        ref_q     <= in_q - ref_dc_q;
        ref_acc_i <= ref_acc_i + in_i - ref_dc_i;
        ref_acc_q <= ref_acc_q + in_q - ref_dc_q;
    end
end

// --- measurement ------------------------------------------------------------------------------
integer n;
integer r_peak, d_peak;                    // peak deviation from the ideal modulation on Q
integer r_early, d_early;                  // same, over the first frame after reset
integer r_dcsum, d_dcsum, dc_n;
integer dev;
reg signed [W-1:0] want_q;
real ratio, ratio_early;

function integer iabs(input integer v);
    iabs = (v < 0) ? -v : v;
endfunction

initial begin
    r_peak = 0; d_peak = 0; r_early = 0; d_early = 0; r_dcsum = 0; d_dcsum = 0; dc_n = 0;
    repeat (4) @(negedge clk);
    rst = 1'b0;
    @(negedge clk);

    for (n = 0; n < NS; n = n + 1) begin
        // I carries DC only; Q carries DC plus a square wave whose half period is one legacy time
        // constant -- a four-symbol run, exactly the frame pattern at bit 189.
        want_q   = ((n / RUN) % 2 == 0) ? AMP : -AMP;
        in_i     = DC_I;
        in_q     = DC_Q + want_q;
        in_valid = 1'b1;
        @(negedge clk);

        if (n > 64 && n < EARLY) begin     // skip the first few samples: neither has any estimate
            dev = iabs(ref_q - want_q); if (dev > r_early) r_early = dev;
            dev = iabs(d_q   - want_q); if (dev > d_early) d_early = dev;
        end
        if (n > SETTLE) begin
            r_dcsum = r_dcsum + ref_i;
            d_dcsum = d_dcsum + d_i;
            dc_n    = dc_n + 1;
            dev = iabs(ref_q - want_q); if (dev > r_peak) r_peak = dev;
            dev = iabs(d_q   - want_q); if (dev > d_peak) d_peak = dev;
        end
    end
    in_valid = 1'b0;
    @(negedge clk);

    $display("residual DC on the quiet axis: original %0d, running-average %0d (injected %0d)",
             r_dcsum / dc_n, d_dcsum / dc_n, DC_I);
    ratio       = (d_peak  == 0) ? 1.0e9 : (1.0 * r_peak)  / (1.0 * d_peak);
    ratio_early = (d_early == 0) ? 1.0e9 : (1.0 * r_early) / (1.0 * d_early);
    $display("steady-state data tracking on Q: original %0d (%.1f%% of amp), new %0d (%.1f%%), %.1fx better",
             r_peak, 100.0 * r_peak / AMP, d_peak, 100.0 * d_peak / AMP, ratio);
    $display("first frame after reset:         original %0d (%.1f%% of amp), new %0d (%.1f%%), %.1fx better",
             r_early, 100.0 * r_early / AMP, d_early, 100.0 * d_early / AMP, ratio_early);

    if (iabs(d_dcsum / dc_n) > DC_I / 10) begin
        $display("FAIL: blocker leaves %0d of the injected DC (>10%%)", d_dcsum / dc_n);
        $fatal(1);
    end
    if (ratio < 4.0) begin
        $display("FAIL: steady-state data tracking only %.1fx better, expected >= 4x", ratio);
        $fatal(1);
    end
    if (ratio_early < 1.0) begin
        $display("FAIL: the estimate is WORSE than the original over the first frame (%.2fx).",
                 ratio_early);
        $display("      That is the failure mode that regressed tb_qpsk_timing_recovery_retained.");
        $fatal(1);
    end
    $display("PASS: DC still removed, data tracking cut %.1fx steady-state and %.1fx over frame one",
             ratio, ratio_early);
    $finish;
end

endmodule
