// Lab 5.12 - decision-directed QPSK Costas carrier-recovery loop (symbol rate).
//
// Ports the validated Python model (Block 8 Lab 8.9 qpsk_carrier_recovery.costas_qpsk,
// and the FishBall PSK_err / NCO / PI reference): a per-symbol NCO de-rotator + a
// decision-directed phase-error detector + a PI loop filter. Sits between the symbol
// sampler and the hard decision. On a real single-board self-OTA link the received
// symbols carry a small but per-burst-jittery carrier phase that a fixed-phase RX
// cannot track (recv=140 but ~44% BER); this loop tracks it and recovers BER=0 (proven
// offline on the captured burst, BER 0/280).
//
//   y = in * exp(-j*theta)                         (NCO de-rotate, cos/sin from LUT)
//   e = sgn(y_I)*y_Q - sgn(y_Q)*y_I                (QPSK decision-directed phase error)
//   freq  += e >>> KI_SHIFT                         (PI integral term)
//   theta += freq + (e >>> KP_SHIFT)               (PI proportional + NCO accumulate)
//
// Enable-gated so the fabric loopback / clean paths keep the pass-through symbols
// bit-identical. The 90-degree QPSK ambiguity the loop leaves is resolved downstream
// by the preamble frame-sync (as in the software model), not here.

`timescale 1ns/1ps

module qpsk_costas #(
    parameter integer W = 16,
    parameter integer PHASE_W = 24,          // NCO phase accumulator width (full scale = 2*pi)
    parameter integer LUT_AW = 8,            // cos/sin LUT address bits (256 entries)
    // Bang-bang loop: the phase-error detector is reduced to its SIGN (+-1), so the loop
    // gain is amplitude-independent (the RTL symbols are un-normalised MF outputs, unlike
    // the unit-amplitude Python model). Each symbol the NCO steps by a fixed phase quantum:
    //   proportional step = 2^KP_LOG, integral step = 2^KI_LOG (in PHASE_W phase units,
    //   full scale 2^PHASE_W = 2*pi). KP_LOG large enough to pull +-pi within the ~12-symbol
    //   preamble; KI_LOG smaller for slow CFO tracking.
    parameter integer KP_LOG = 18,
    parameter integer KI_LOG = 12,
    parameter LUT_FILE = "blocks/block_05_fpga_hdl_flow/rtl/cos_sin_lut.mem"
) (
    input  wire                 clk,
    input  wire                 rst,
    input  wire                 enable,      // 1 = carrier tracking; 0 = pass-through
    input  wire                 in_valid,
    input  wire signed [W-1:0]  in_i,
    input  wire signed [W-1:0]  in_q,
    output reg                  out_valid,
    output reg  signed [W-1:0]  out_i,
    output reg  signed [W-1:0]  out_q
);

// cos/sin LUT: entry = {cos[15:0], sin[15:0]} in Q15.
reg [31:0] cos_sin [0:(1<<LUT_AW)-1];
integer li;
initial begin
    for (li = 0; li < (1<<LUT_AW); li = li + 1) cos_sin[li] = 32'd0;
    $readmemh(LUT_FILE, cos_sin);
end

reg signed [PHASE_W-1:0] theta = {PHASE_W{1'b0}};
reg signed [PHASE_W-1:0] freq  = {PHASE_W{1'b0}};

// Negated phase index (rotation by -theta): use -theta's top LUT_AW bits.
wire signed [PHASE_W-1:0] ntheta = -theta;
wire [LUT_AW-1:0] lut_idx = ntheta[PHASE_W-1 -: LUT_AW];
wire signed [15:0] cos_v = cos_sin[lut_idx][31:16];
wire signed [15:0] sin_v = cos_sin[lut_idx][15:0];

// y = in * exp(-j*theta): with (cos,sin) already the cos/sin of -theta,
//   y_I = in_I*cos - in_Q*sin ; y_Q = in_I*sin + in_Q*cos.
wire signed [W+16-1:0] mult_ic = in_i * cos_v;
wire signed [W+16-1:0] mult_qs = in_q * sin_v;
wire signed [W+16-1:0] mult_is = in_i * sin_v;
wire signed [W+16-1:0] mult_qc = in_q * cos_v;
wire signed [W-1:0] y_i = (mult_ic - mult_qs) >>> 15;   // back to Q of the input (÷2^15)
wire signed [W-1:0] y_q = (mult_is + mult_qc) >>> 15;

// decision-directed QPSK phase error: e = sgn(y_I)*y_Q - sgn(y_Q)*y_I.
wire signed [W-1:0] term_a = y_i[W-1] ? -y_q :  y_q;    // sgn(y_I)*y_Q  (sgn: y_I<0 -> -)
wire signed [W-1:0] term_b = y_q[W-1] ? -y_i :  y_i;    // sgn(y_Q)*y_I
wire signed [W:0]   e_raw  = term_a - term_b;           // one guard bit
// bang-bang: only the SIGN of the phase error drives the loop (amplitude-independent)
wire signed [1:0] e_bb = (e_raw > 0) ? 2'sd1 : ((e_raw < 0) ? -2'sd1 : 2'sd0);
wire signed [PHASE_W-1:0] kp_step = $signed({{(PHASE_W-2){e_bb[1]}}, e_bb}) <<< KP_LOG;
wire signed [PHASE_W-1:0] ki_step = $signed({{(PHASE_W-2){e_bb[1]}}, e_bb}) <<< KI_LOG;

always @(posedge clk) begin
    if (rst) begin
        theta     <= {PHASE_W{1'b0}};
        freq      <= {PHASE_W{1'b0}};
        out_valid <= 1'b0;
        out_i     <= {W{1'b0}};
        out_q     <= {W{1'b0}};
    end else begin
        out_valid <= in_valid;
        if (in_valid) begin
            out_i <= enable ? y_i : in_i;
            out_q <= enable ? y_q : in_q;
            if (enable) begin
                // PI loop + NCO accumulate (phase wraps naturally at PHASE_W).
                freq  <= freq + ki_step;
                theta <= theta + freq + kp_step;
            end
        end
    end
end

endmodule
