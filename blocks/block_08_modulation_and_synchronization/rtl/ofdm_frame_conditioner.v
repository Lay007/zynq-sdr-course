`timescale 1ns/1ps

// Issue #48: between ofdm_frame_sync and the modem's receiver, a coarse carrier-offset correction and
// a level normalization for each frame, both from the preamble that ofdm_frame_sync has just measured.
//
// CFO. The sum of P over the plateau has the angle theta = 2*pi*32*eps (eps = CFO in cycles per
// sample), unambiguous for |eps| < 1/64: +-32.5 kHz at 2.083 MS/s, twice the modem's own CP-based
// corrector (+-1/128). A sequential CORDIC (16 iterations) gives theta in 1/65536 of a turn; the NCO
// then adds eps = theta / 2^21 turns per sample (2^-24 turns: theta * 8) and every sample of the frame
// is turned by -phase (sin/cos from ofdm_sin_rom, 1024 steps per turn). The modem corrects what is
// left. The phase starts at 0 with the frame's first sample; the equalizer takes any constant phase.
//
// Level. R = 32 * mean |x|^2 of the 12-bit samples (>> SHIFT, as ofdm_frame_sync gives it); the frame
// is passed on in Q1.15 as 16 * x after RX_SHIFT = 4, so its mean power is 8 * R * 2^SHIFT. The gain
// 2^(k/2), k = TARGET_LOG2 - round(log2(R * 2^SHIFT)), brings the RMS to about 4096 (between 3444 and
// 4870: 3 dB steps), whatever the radio's gain was. k is limited to -16..16.
//
// DC. The samples come from ofdm_frame_sync's delay line, not DC-tracked: the modem does not use
// subcarrier 0, so a DC offset did not matter. Turned by the CFO correction it would become a tone at
// -CFO, between the data subcarriers (tb_ofdm_radio_core at -28 kHz and -20 dB: bit errors). So with
// cfo_en the tracker's estimate at the frame's detection is subtracted first.
//
// cfo_en = 0 or agc_en = 0 passes the samples through that stage unchanged (theta or k then read 0).
module ofdm_frame_conditioner #(
    parameter integer SHIFT = 8,            // ofdm_frame_sync's SHIFT
    parameter integer TARGET_LOG2 = 21
) (
    input  wire               clk,
    input  wire               rst,
    input  wire               cfo_en,
    input  wire               agc_en,
    input  wire               est_valid,
    input  wire signed [35:0] est_re,
    input  wire signed [35:0] est_im,
    input  wire        [31:0] est_r,
    input  wire signed [15:0] est_dc_re,     // subtracted from every sample before the rotation
    input  wire signed [15:0] est_dc_im,
    input  wire               in_valid,
    output wire               in_ready,
    input  wire signed [15:0] in_re,
    input  wire signed [15:0] in_im,
    input  wire               in_last,
    input  wire               in_start,
    output wire               out_valid,
    input  wire               out_ready,
    output wire signed [15:0] out_re,
    output wire signed [15:0] out_im,
    output wire               out_last,
    output reg  signed [15:0] theta = 0,     // preamble angle, 2^16 = one turn
    output reg  signed [5:0]  gain_k = 0,    // gain 2^(k/2)
    output reg                busy = 1'b0    // CORDIC running (a frame should not start before it ends)
);

// ---------------------------------------------------------------------------------------------
// CORDIC vectoring: theta = atan2(est_im, est_re)
// ---------------------------------------------------------------------------------------------
function [15:0] atan_tab(input [3:0] i);    // round(atan(2^-i) / (2*pi) * 65536)
    case (i)
    4'd0: atan_tab = 16'd8192;  4'd1: atan_tab = 16'd4836;  4'd2: atan_tab = 16'd2555;  4'd3: atan_tab = 16'd1297;
    4'd4: atan_tab = 16'd651;   4'd5: atan_tab = 16'd326;   4'd6: atan_tab = 16'd163;   4'd7: atan_tab = 16'd81;
    4'd8: atan_tab = 16'd41;    4'd9: atan_tab = 16'd20;    4'd10: atan_tab = 16'd10;   4'd11: atan_tab = 16'd5;
    4'd12: atan_tab = 16'd3;    4'd13: atan_tab = 16'd1;    4'd14: atan_tab = 16'd1;    default: atan_tab = 16'd0;
    endcase
endfunction

reg signed [38:0] cx = 0, cy = 0;
reg signed [15:0] cz = 0;
reg        [3:0]  ci = 0;

// log2 of R * 2^SHIFT, rounded: the position of the top bit, + 1 when the mantissa (its top 4 bits,
// 1.mmm) is >= 1.375 (the exact point is sqrt(2) = 1.414; the error is a fraction of the 3 dB step)
function integer msb32(input [31:0] v);
    integer b;
    begin
        msb32 = -1;
        for (b = 0; b < 32; b = b + 1)
            if (v[b]) msb32 = b;
    end
endfunction
integer k_calc;
reg [31:0] r_norm;

// Level, over three clocks (once per frame; in one clock the priority encoder, the normalizing
// shift and the subtraction were 15 logic levels): R registered, its top bit found, then k.
reg        lv1 = 1'b0, lv2 = 1'b0, lz1 = 1'b0;
reg [31:0] r1 = 0, r2 = 0;
reg signed [6:0] m2 = 0;
always @(posedge clk) begin
    lv1 <= est_valid && agc_en;
    lz1 <= est_valid && !agc_en;
    r1 <= est_r;
    lv2 <= lv1;
    r2 <= r1;
    m2 <= msb32(r1);
    if (rst || lz1) begin
        gain_k <= 0;
    end else if (lv2) begin
        if (m2 < 0) begin
            gain_k <= 0;
        end else begin
            r_norm = (m2 >= 3) ? (r2 >> (m2 - 3)) : (r2 << (3 - m2));     // 1mmm, top 4 bits
            k_calc = TARGET_LOG2 - (m2 + SHIFT + ((r_norm[2:0] >= 3'd3) ? 1 : 0));
            gain_k <= (k_calc > 16) ? 6'sd16 : (k_calc < -16) ? -6'sd16 : k_calc[5:0];
        end
    end
end

always @(posedge clk) begin
    if (rst) begin
        busy <= 1'b0;
        theta <= 0;
    end else if (est_valid) begin
        // CFO: bring the vector into the right half plane, then iterate
        if (est_re < 0) begin
            cx <= -est_re; cy <= -est_im; cz <= 16'sh8000;
        end else begin
            cx <= est_re; cy <= est_im; cz <= 16'sd0;
        end
        ci <= 0;
        busy <= cfo_en;
        if (!cfo_en) theta <= 0;
    end else if (busy) begin
        if (cy >= 0) begin
            cx <= cx + (cy >>> ci);
            cy <= cy - (cx >>> ci);
            cz <= cz + atan_tab(ci);
        end else begin
            cx <= cx - (cy >>> ci);
            cy <= cy + (cx >>> ci);
            cz <= cz - atan_tab(ci);
        end
        ci <= ci + 1'b1;
        if (ci == 4'd15) begin
            busy <= 1'b0;
            theta <= cz;
        end
    end
end

// ---------------------------------------------------------------------------------------------
// Datapath: NCO rotation, gain, saturation (pipeline with one enable)
// ---------------------------------------------------------------------------------------------
wire        en = !out_valid || out_ready;
assign in_ready = en;

reg  [23:0] nco = 0;
wire signed [23:0] inc = cfo_en ? {{5{theta[15]}}, theta, 3'b000} : 24'sd0;      // theta * 8
wire signed [15:0] s_sin, s_cos;
reg  [9:0]  ph0 = 0;
ofdm_sin_rom sin_rom (.phase(ph0), .sin_out(s_sin), .cos_out(s_cos));

reg signed [15:0] dc_re = 0, dc_im = 0;
always @(posedge clk)
    if (rst) begin
        dc_re <= 0;
        dc_im <= 0;
    end else if (est_valid) begin
        dc_re <= est_dc_re;
        dc_im <= est_dc_im;
    end
function [15:0] sat16s(input signed [16:0] v);
    begin
        if (v > 17'sd32767) sat16s = 16'h7FFF;
        else if (v < -17'sd32768) sat16s = 16'h8000;
        else sat16s = v[15:0];
    end
endfunction

// stage 0: the sample (less the DC) and its phase
reg               v0 = 1'b0, l0 = 1'b0;
reg signed [15:0] x0_re = 0, x0_im = 0;
// stage 1: products
reg               v1 = 1'b0, l1 = 1'b0;
reg signed [31:0] p_rc = 0, p_is = 0, p_ic = 0, p_rs = 0;
reg signed [15:0] x1_re = 0, x1_im = 0;
// stage 2: rotated, Q1.15 (17 bits)
reg               v2 = 1'b0, l2 = 1'b0;
reg signed [16:0] y2_re = 0, y2_im = 0;
// stage 3: times the gain mantissa (1 or sqrt(2), Q2.14)
reg               v3 = 1'b0, l3 = 1'b0;
reg signed [33:0] g3_re = 0, g3_im = 0;
// stages 4-6: rounding constant added, shifted, saturated. The gain changes once per frame, long
// before the frame's samples, so the shift and the rounding constant are registers of their own:
// computed from gain_k in the same clock as the product, the path ran gain_k -> rounding constant
// -> DSP -> 34-bit variable shift -> saturation in one clock (Vivado OOC: +0.002 ns).
reg               v4 = 1'b0, l4 = 1'b0, v5 = 1'b0, l5 = 1'b0, v6 = 1'b0, l6 = 1'b0;
reg signed [33:0] a4_re = 0, a4_im = 0, s5_re = 0, s5_im = 0;
reg signed [15:0] o_re = 0, o_im = 0;

wire signed [5:0] k_half = gain_k >>> 1;                   // floor(k / 2)
reg        [15:0] mant = 16'd16384;
reg        [4:0]  rsh = 5'd14;                             // right shift after the Q2.14 product: 6..22
reg signed [33:0] rnd = 34'sd8192;                         // 2^(rsh - 1)
always @(posedge clk) begin
    mant <= gain_k[0] ? 16'd23170 : 16'd16384;
    rsh <= 5'd14 - k_half[4:0];
    rnd <= 34'sd1 <<< (5'd13 - k_half[4:0]);
end

function [15:0] sat(input signed [33:0] v);
    begin
        if (v > 34'sd32767) sat = 16'h7FFF;
        else if (v < -34'sd32768) sat = 16'h8000;
        else sat = v[15:0];
    end
endfunction

always @(posedge clk) begin
    if (rst) begin
        {v0, v1, v2, v3, v4, v5, v6} <= 7'd0;
        nco <= 0;
    end else if (en) begin
        // stage 0
        v0 <= in_valid;
        if (in_valid) begin
            x0_re <= cfo_en ? sat16s(in_re - dc_re) : in_re;
            x0_im <= cfo_en ? sat16s(in_im - dc_im) : in_im;
            l0 <= in_last;
            ph0 <= in_start ? 10'd0 : nco[23:14];
            nco <= in_start ? inc : nco + inc;
        end
        // stage 1: x * e^(-j phase)
        v1 <= v0; l1 <= l0;
        p_rc <= x0_re * s_cos;
        p_is <= x0_im * s_sin;
        p_ic <= x0_im * s_cos;
        p_rs <= x0_re * s_sin;
        x1_re <= x0_re;
        x1_im <= x0_im;
        // stage 2
        v2 <= v1; l2 <= l1;
        if (cfo_en) begin
            y2_re <= (p_rc + p_is + 32'sd16384) >>> 15;
            y2_im <= (p_ic - p_rs + 32'sd16384) >>> 15;
        end else begin
            y2_re <= x1_re;
            y2_im <= x1_im;
        end
        // stage 3
        v3 <= v2; l3 <= l2;
        g3_re <= y2_re * $signed({1'b0, mant});
        g3_im <= y2_im * $signed({1'b0, mant});
        // stage 4: + rounding constant
        v4 <= v3; l4 <= l3;
        a4_re <= g3_re + rnd;
        a4_im <= g3_im + rnd;
        // stage 5: shift (rsh is 6..22, always to the right)
        v5 <= v4; l5 <= l4;
        s5_re <= a4_re >>> rsh;
        s5_im <= a4_im >>> rsh;
        // stage 6: saturate
        v6 <= v5; l6 <= l5;
        o_re <= sat(s5_re);
        o_im <= sat(s5_im);
    end
end

assign out_valid = v6;
assign out_re = o_re;
assign out_im = o_im;
assign out_last = l6;

endmodule
