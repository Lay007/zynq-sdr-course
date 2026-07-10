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
    // Linear decision-directed PED with LEFT-shift loop gains (e ~ A*phase_error, A =
    // un-normalised MF amplitude, so the NCO step shifts UP into phase units; full scale
    // 2^PHASE_W = 2*pi). Proportional step = e_ext <<< KP_LOG, integral/frequency step =
    // e_ext <<< KI_LOG (< KP_LOG).
    //
    // GEAR SHIFT. The proportional gain wants to be two different things. Pull-in must
    // finish inside the 12-symbol preamble or the frame-sync correlates against a still-
    // rotating constellation, and the loop removes phase modulo 90 degrees so it can face
    // a +-45-degree error: that needs a wide loop. Tracking wants the opposite -- a wide
    // loop passes more noise into theta and slips a quadrant mid-frame (measured: 6 of 40
    // hardware bursts locked, then took ~86 of 280 bit errors, i.e. half the bits after a
    // slip ~40% into the frame). So acquire with KP_LOG_ACQ for ACQ_SYMBOLS symbols, then
    // drop to the quiet KP_LOG_TRACK. KP_LOG=6 alone corrects ~4% of the phase error per
    // symbol (~27-symbol time constant) and never settles in 12; KP_LOG=8 alone acquires
    // every angle but tracks noisily.
    //
    // ACQ_SYMBOLS counts the symbols the loop actually RAN on, i.e. from the moment the
    // freeze gate opens. That is not the start of the frame: the gate trips on the RRC
    // ramp, measured 16 symbols before the frame-sync latches (gate at symbol 15, lock at
    // symbol 31 on the real self-OTA capture). ACQ_SYMBOLS=16 therefore expired exactly at
    // the lock instant, and any burst whose gate opened a symbol early finished its
    // preamble on the slow loop -- 8 of 40 hardware bursts then locked a quadrant off
    // (~125 of 280 bit errors). 32 leaves 2x margin and still hands the frame to the quiet
    // loop long before the mid-frame slips (~symbol 56) it exists to prevent.
    parameter integer KP_LOG_ACQ = 8,
    parameter integer KP_LOG_TRACK = 6,
    parameter integer ACQ_SYMBOLS = 32,
    parameter integer KI_LOG = 1,
    // FREEZE GATE (burst-mode acquisition). The RX chain resets the loop per frame, and a
    // real burst starts with pre-frame NOISE (the AD9361 round-trip latency). Without a
    // gate the loop wanders on that noise and cannot settle by the time the ~12-symbol
    // preamble arrives -> no frame-sync lock. When |in_i|+|in_q| < SIG_THRESH the loop
    // HOLDS theta/freq (freezes), so it starts acquiring from a clean held phase exactly
    // when the frame (high magnitude) arrives. 0 disables the gate (always update).
    parameter integer SIG_THRESH = 1000
) (
    input  wire                 clk,
    input  wire                 rst,         // clears the output pipeline and the gear-shift counter
    // Clears the NCO phase / frequency accumulators. Usually tied to `rst`. Driving it
    // separately lets a burst-mode receiver KEEP the carrier phase across frames: the RF
    // path phase is quasi-static and the freeze gate already holds theta through the
    // inter-burst silence, so the next burst starts near the right phase instead of
    // pulling in from zero. Harmless when the phase does drift -- the loop just re-acquires.
    input  wire                 rst_phase,
    input  wire                 enable,      // 1 = carrier tracking; 0 = pass-through
    input  wire                 in_valid,
    input  wire signed [W-1:0]  in_i,
    input  wire signed [W-1:0]  in_q,
    output reg                  out_valid,
    output reg  signed [W-1:0]  out_i,
    output reg  signed [W-1:0]  out_q
);

// cos/sin LUT: entry = {cos[15:0], sin[15:0]} in Q15, EMBEDDED in the RTL.
// (An external $readmemh file is not used: Vivado synthesis could not resolve the
// relative path and silently loaded an all-zero table, which killed the loop on
// hardware while iverilog -- run from the repo root -- loaded it fine.)
reg [31:0] cos_sin [0:255];
initial begin
    cos_sin[  0] = 32'h7fff0000;
    cos_sin[  1] = 32'h7ff50324;
    cos_sin[  2] = 32'h7fd80648;
    cos_sin[  3] = 32'h7fa6096a;
    cos_sin[  4] = 32'h7f610c8c;
    cos_sin[  5] = 32'h7f090fab;
    cos_sin[  6] = 32'h7e9c12c8;
    cos_sin[  7] = 32'h7e1d15e2;
    cos_sin[  8] = 32'h7d8918f9;
    cos_sin[  9] = 32'h7ce31c0b;
    cos_sin[ 10] = 32'h7c291f1a;
    cos_sin[ 11] = 32'h7b5c2223;
    cos_sin[ 12] = 32'h7a7c2528;
    cos_sin[ 13] = 32'h79892826;
    cos_sin[ 14] = 32'h78842b1f;
    cos_sin[ 15] = 32'h776b2e11;
    cos_sin[ 16] = 32'h764130fb;
    cos_sin[ 17] = 32'h750433df;
    cos_sin[ 18] = 32'h73b536ba;
    cos_sin[ 19] = 32'h7254398c;
    cos_sin[ 20] = 32'h70e23c56;
    cos_sin[ 21] = 32'h6f5e3f17;
    cos_sin[ 22] = 32'h6dc941ce;
    cos_sin[ 23] = 32'h6c23447a;
    cos_sin[ 24] = 32'h6a6d471c;
    cos_sin[ 25] = 32'h68a649b4;
    cos_sin[ 26] = 32'h66cf4c3f;
    cos_sin[ 27] = 32'h64e84ebf;
    cos_sin[ 28] = 32'h62f15133;
    cos_sin[ 29] = 32'h60eb539b;
    cos_sin[ 30] = 32'h5ed755f5;
    cos_sin[ 31] = 32'h5cb35842;
    cos_sin[ 32] = 32'h5a825a82;
    cos_sin[ 33] = 32'h58425cb3;
    cos_sin[ 34] = 32'h55f55ed7;
    cos_sin[ 35] = 32'h539b60eb;
    cos_sin[ 36] = 32'h513362f1;
    cos_sin[ 37] = 32'h4ebf64e8;
    cos_sin[ 38] = 32'h4c3f66cf;
    cos_sin[ 39] = 32'h49b468a6;
    cos_sin[ 40] = 32'h471c6a6d;
    cos_sin[ 41] = 32'h447a6c23;
    cos_sin[ 42] = 32'h41ce6dc9;
    cos_sin[ 43] = 32'h3f176f5e;
    cos_sin[ 44] = 32'h3c5670e2;
    cos_sin[ 45] = 32'h398c7254;
    cos_sin[ 46] = 32'h36ba73b5;
    cos_sin[ 47] = 32'h33df7504;
    cos_sin[ 48] = 32'h30fb7641;
    cos_sin[ 49] = 32'h2e11776b;
    cos_sin[ 50] = 32'h2b1f7884;
    cos_sin[ 51] = 32'h28267989;
    cos_sin[ 52] = 32'h25287a7c;
    cos_sin[ 53] = 32'h22237b5c;
    cos_sin[ 54] = 32'h1f1a7c29;
    cos_sin[ 55] = 32'h1c0b7ce3;
    cos_sin[ 56] = 32'h18f97d89;
    cos_sin[ 57] = 32'h15e27e1d;
    cos_sin[ 58] = 32'h12c87e9c;
    cos_sin[ 59] = 32'h0fab7f09;
    cos_sin[ 60] = 32'h0c8c7f61;
    cos_sin[ 61] = 32'h096a7fa6;
    cos_sin[ 62] = 32'h06487fd8;
    cos_sin[ 63] = 32'h03247ff5;
    cos_sin[ 64] = 32'h00007fff;
    cos_sin[ 65] = 32'hfcdc7ff5;
    cos_sin[ 66] = 32'hf9b87fd8;
    cos_sin[ 67] = 32'hf6967fa6;
    cos_sin[ 68] = 32'hf3747f61;
    cos_sin[ 69] = 32'hf0557f09;
    cos_sin[ 70] = 32'hed387e9c;
    cos_sin[ 71] = 32'hea1e7e1d;
    cos_sin[ 72] = 32'he7077d89;
    cos_sin[ 73] = 32'he3f57ce3;
    cos_sin[ 74] = 32'he0e67c29;
    cos_sin[ 75] = 32'hdddd7b5c;
    cos_sin[ 76] = 32'hdad87a7c;
    cos_sin[ 77] = 32'hd7da7989;
    cos_sin[ 78] = 32'hd4e17884;
    cos_sin[ 79] = 32'hd1ef776b;
    cos_sin[ 80] = 32'hcf057641;
    cos_sin[ 81] = 32'hcc217504;
    cos_sin[ 82] = 32'hc94673b5;
    cos_sin[ 83] = 32'hc6747254;
    cos_sin[ 84] = 32'hc3aa70e2;
    cos_sin[ 85] = 32'hc0e96f5e;
    cos_sin[ 86] = 32'hbe326dc9;
    cos_sin[ 87] = 32'hbb866c23;
    cos_sin[ 88] = 32'hb8e46a6d;
    cos_sin[ 89] = 32'hb64c68a6;
    cos_sin[ 90] = 32'hb3c166cf;
    cos_sin[ 91] = 32'hb14164e8;
    cos_sin[ 92] = 32'haecd62f1;
    cos_sin[ 93] = 32'hac6560eb;
    cos_sin[ 94] = 32'haa0b5ed7;
    cos_sin[ 95] = 32'ha7be5cb3;
    cos_sin[ 96] = 32'ha57e5a82;
    cos_sin[ 97] = 32'ha34d5842;
    cos_sin[ 98] = 32'ha12955f5;
    cos_sin[ 99] = 32'h9f15539b;
    cos_sin[100] = 32'h9d0f5133;
    cos_sin[101] = 32'h9b184ebf;
    cos_sin[102] = 32'h99314c3f;
    cos_sin[103] = 32'h975a49b4;
    cos_sin[104] = 32'h9593471c;
    cos_sin[105] = 32'h93dd447a;
    cos_sin[106] = 32'h923741ce;
    cos_sin[107] = 32'h90a23f17;
    cos_sin[108] = 32'h8f1e3c56;
    cos_sin[109] = 32'h8dac398c;
    cos_sin[110] = 32'h8c4b36ba;
    cos_sin[111] = 32'h8afc33df;
    cos_sin[112] = 32'h89bf30fb;
    cos_sin[113] = 32'h88952e11;
    cos_sin[114] = 32'h877c2b1f;
    cos_sin[115] = 32'h86772826;
    cos_sin[116] = 32'h85842528;
    cos_sin[117] = 32'h84a42223;
    cos_sin[118] = 32'h83d71f1a;
    cos_sin[119] = 32'h831d1c0b;
    cos_sin[120] = 32'h827718f9;
    cos_sin[121] = 32'h81e315e2;
    cos_sin[122] = 32'h816412c8;
    cos_sin[123] = 32'h80f70fab;
    cos_sin[124] = 32'h809f0c8c;
    cos_sin[125] = 32'h805a096a;
    cos_sin[126] = 32'h80280648;
    cos_sin[127] = 32'h800b0324;
    cos_sin[128] = 32'h80010000;
    cos_sin[129] = 32'h800bfcdc;
    cos_sin[130] = 32'h8028f9b8;
    cos_sin[131] = 32'h805af696;
    cos_sin[132] = 32'h809ff374;
    cos_sin[133] = 32'h80f7f055;
    cos_sin[134] = 32'h8164ed38;
    cos_sin[135] = 32'h81e3ea1e;
    cos_sin[136] = 32'h8277e707;
    cos_sin[137] = 32'h831de3f5;
    cos_sin[138] = 32'h83d7e0e6;
    cos_sin[139] = 32'h84a4dddd;
    cos_sin[140] = 32'h8584dad8;
    cos_sin[141] = 32'h8677d7da;
    cos_sin[142] = 32'h877cd4e1;
    cos_sin[143] = 32'h8895d1ef;
    cos_sin[144] = 32'h89bfcf05;
    cos_sin[145] = 32'h8afccc21;
    cos_sin[146] = 32'h8c4bc946;
    cos_sin[147] = 32'h8dacc674;
    cos_sin[148] = 32'h8f1ec3aa;
    cos_sin[149] = 32'h90a2c0e9;
    cos_sin[150] = 32'h9237be32;
    cos_sin[151] = 32'h93ddbb86;
    cos_sin[152] = 32'h9593b8e4;
    cos_sin[153] = 32'h975ab64c;
    cos_sin[154] = 32'h9931b3c1;
    cos_sin[155] = 32'h9b18b141;
    cos_sin[156] = 32'h9d0faecd;
    cos_sin[157] = 32'h9f15ac65;
    cos_sin[158] = 32'ha129aa0b;
    cos_sin[159] = 32'ha34da7be;
    cos_sin[160] = 32'ha57ea57e;
    cos_sin[161] = 32'ha7bea34d;
    cos_sin[162] = 32'haa0ba129;
    cos_sin[163] = 32'hac659f15;
    cos_sin[164] = 32'haecd9d0f;
    cos_sin[165] = 32'hb1419b18;
    cos_sin[166] = 32'hb3c19931;
    cos_sin[167] = 32'hb64c975a;
    cos_sin[168] = 32'hb8e49593;
    cos_sin[169] = 32'hbb8693dd;
    cos_sin[170] = 32'hbe329237;
    cos_sin[171] = 32'hc0e990a2;
    cos_sin[172] = 32'hc3aa8f1e;
    cos_sin[173] = 32'hc6748dac;
    cos_sin[174] = 32'hc9468c4b;
    cos_sin[175] = 32'hcc218afc;
    cos_sin[176] = 32'hcf0589bf;
    cos_sin[177] = 32'hd1ef8895;
    cos_sin[178] = 32'hd4e1877c;
    cos_sin[179] = 32'hd7da8677;
    cos_sin[180] = 32'hdad88584;
    cos_sin[181] = 32'hdddd84a4;
    cos_sin[182] = 32'he0e683d7;
    cos_sin[183] = 32'he3f5831d;
    cos_sin[184] = 32'he7078277;
    cos_sin[185] = 32'hea1e81e3;
    cos_sin[186] = 32'hed388164;
    cos_sin[187] = 32'hf05580f7;
    cos_sin[188] = 32'hf374809f;
    cos_sin[189] = 32'hf696805a;
    cos_sin[190] = 32'hf9b88028;
    cos_sin[191] = 32'hfcdc800b;
    cos_sin[192] = 32'h00008001;
    cos_sin[193] = 32'h0324800b;
    cos_sin[194] = 32'h06488028;
    cos_sin[195] = 32'h096a805a;
    cos_sin[196] = 32'h0c8c809f;
    cos_sin[197] = 32'h0fab80f7;
    cos_sin[198] = 32'h12c88164;
    cos_sin[199] = 32'h15e281e3;
    cos_sin[200] = 32'h18f98277;
    cos_sin[201] = 32'h1c0b831d;
    cos_sin[202] = 32'h1f1a83d7;
    cos_sin[203] = 32'h222384a4;
    cos_sin[204] = 32'h25288584;
    cos_sin[205] = 32'h28268677;
    cos_sin[206] = 32'h2b1f877c;
    cos_sin[207] = 32'h2e118895;
    cos_sin[208] = 32'h30fb89bf;
    cos_sin[209] = 32'h33df8afc;
    cos_sin[210] = 32'h36ba8c4b;
    cos_sin[211] = 32'h398c8dac;
    cos_sin[212] = 32'h3c568f1e;
    cos_sin[213] = 32'h3f1790a2;
    cos_sin[214] = 32'h41ce9237;
    cos_sin[215] = 32'h447a93dd;
    cos_sin[216] = 32'h471c9593;
    cos_sin[217] = 32'h49b4975a;
    cos_sin[218] = 32'h4c3f9931;
    cos_sin[219] = 32'h4ebf9b18;
    cos_sin[220] = 32'h51339d0f;
    cos_sin[221] = 32'h539b9f15;
    cos_sin[222] = 32'h55f5a129;
    cos_sin[223] = 32'h5842a34d;
    cos_sin[224] = 32'h5a82a57e;
    cos_sin[225] = 32'h5cb3a7be;
    cos_sin[226] = 32'h5ed7aa0b;
    cos_sin[227] = 32'h60ebac65;
    cos_sin[228] = 32'h62f1aecd;
    cos_sin[229] = 32'h64e8b141;
    cos_sin[230] = 32'h66cfb3c1;
    cos_sin[231] = 32'h68a6b64c;
    cos_sin[232] = 32'h6a6db8e4;
    cos_sin[233] = 32'h6c23bb86;
    cos_sin[234] = 32'h6dc9be32;
    cos_sin[235] = 32'h6f5ec0e9;
    cos_sin[236] = 32'h70e2c3aa;
    cos_sin[237] = 32'h7254c674;
    cos_sin[238] = 32'h73b5c946;
    cos_sin[239] = 32'h7504cc21;
    cos_sin[240] = 32'h7641cf05;
    cos_sin[241] = 32'h776bd1ef;
    cos_sin[242] = 32'h7884d4e1;
    cos_sin[243] = 32'h7989d7da;
    cos_sin[244] = 32'h7a7cdad8;
    cos_sin[245] = 32'h7b5cdddd;
    cos_sin[246] = 32'h7c29e0e6;
    cos_sin[247] = 32'h7ce3e3f5;
    cos_sin[248] = 32'h7d89e707;
    cos_sin[249] = 32'h7e1dea1e;
    cos_sin[250] = 32'h7e9ced38;
    cos_sin[251] = 32'h7f09f055;
    cos_sin[252] = 32'h7f61f374;
    cos_sin[253] = 32'h7fa6f696;
    cos_sin[254] = 32'h7fd8f9b8;
    cos_sin[255] = 32'h7ff5fcdc;
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
wire signed [W:0]   e_raw  = term_a - term_b;           // one guard bit; e ~ A*phase_error
// Linear PED with LEFT-shift loop gains: the error scales with the (un-normalised) symbol
// amplitude A, so the NCO step must be shifted UP into phase units (full scale 2^PHASE_W
// = 2*pi). A linear error makes the loop SETTLE (unlike bang-bang, which limit-cycles);
// the KP_LOG_* pair sets the proportional gain, KI_LOG the slow integral / frequency term.
wire signed [PHASE_W-1:0] e_ext  = {{(PHASE_W-(W+1)){e_raw[W]}}, e_raw};

// Gear shift: wide loop while acquiring, quiet loop once the preamble is behind us.
reg [15:0] acq_cnt = 16'd0;
wire acquiring = (acq_cnt < ACQ_SYMBOLS[15:0]);
wire signed [PHASE_W-1:0] kp_step = acquiring ? (e_ext <<< KP_LOG_ACQ)
                                              : (e_ext <<< KP_LOG_TRACK);
wire signed [PHASE_W-1:0] ki_step = e_ext <<< KI_LOG;

// Freeze gate: run the loop only when a signal is present (|in_i|+|in_q| >= SIG_THRESH).
wire [W-1:0] abs_ii = in_i[W-1] ? (~in_i + 1'b1) : in_i;
wire [W-1:0] abs_qq = in_q[W-1] ? (~in_q + 1'b1) : in_q;
wire loop_run = (SIG_THRESH == 0) || (({1'b0, abs_ii} + {1'b0, abs_qq}) >= SIG_THRESH[W:0]);

// theta/freq follow rst_phase (usually == rst); the pipeline and the gear-shift counter
// follow rst, so a receiver that holds its phase across bursts still re-acquires with the
// wide loop on each new frame -- when the held phase is already right the error is small,
// so the wide gain costs nothing.
always @(posedge clk) begin
    if (rst_phase) begin
        theta <= {PHASE_W{1'b0}};
        freq  <= {PHASE_W{1'b0}};
    end else if (in_valid && enable && loop_run) begin
        // PI loop + NCO accumulate (phase wraps naturally at PHASE_W).
        // Frozen (held) while no signal is present, so the loop does not wander
        // on the pre-frame noise and acquires cleanly when the burst arrives.
        freq  <= freq + ki_step;
        theta <= theta + freq + kp_step;
    end
end

always @(posedge clk) begin
    if (rst) begin
        acq_cnt   <= 16'd0;
        out_valid <= 1'b0;
        out_i     <= {W{1'b0}};
        out_q     <= {W{1'b0}};
    end else begin
        out_valid <= in_valid;
        if (in_valid) begin
            out_i <= enable ? y_i : in_i;
            out_q <= enable ? y_q : in_q;
            // Count only the symbols the loop actually ran on, so the acquisition window
            // starts when the burst arrives, not when the (silent) frame window opens.
            if (enable && loop_run && acquiring) acq_cnt <= acq_cnt + 1'b1;
        end
    end
end

endmodule
