// Lab 5.15 - differential QPSK decoder (rotation-ambiguity remover)
//
// The four-branch frame sync resolves the QPSK 90-degree ambiguity by correlation, and on the
// two-board link it mis-resolves ~1% of bursts (whole-burst wrong rotation, ~46% BER). Differential
// decoding removes the ambiguity at the source: the information is the PHASE DIFFERENCE between
// consecutive symbols, so a constant rotation of the whole burst cancels. Validated offline in
// lab_11_43_dqpsk_model.py: BER 0 under all four rotations, and a mid-burst carrier slip costs one
// bit instead of the whole tail.
//
// Phase index p of a Gray dibit d=(d0=Isign, d1=Qsign), matching qpsk_symbol_mapper /
// qpsk_hard_decision: (0,0)=0deg-quadrant .. ordered around the circle so a 90-degree rotation is
// p -> (p+1) mod 4. The Gray<->binary conversion is p = {d1, d0^d1}, d = {p1, p0^p1}.
//
// Decode: info = (p[n] - p[n-1]) mod 4, i.e. a 2-bit subtract with natural wraparound. The reference
// p[n-1] is simply the previous symbol in the CONTINUOUS stream -- no extra reference symbol and no
// frame-length change, because the transmitter replays cyclically and the frame's total phase
// increment is 0 mod 4 (checked in the model). Reset clears the reference once at burst start; the
// first decoded symbol is then pre-frame noise, which the frame sync discards anyway.
//
// enable=0 is a bit-exact passthrough of the absolute dibit, so the coherent fabric loopback and the
// existing OTA path are unchanged when differential mode is off.

`timescale 1ns/1ps

module qpsk_diff_decoder (
    input  wire       clk,
    input  wire       rst,
    input  wire       enable,       // 1 = differential decode, 0 = pass the absolute dibit through
    input  wire       in_valid,
    input  wire [1:0] in_dibit,     // absolute Gray dibit from the hard decision (in_dibit[0]=I sign)
    output reg        out_valid,
    output reg  [1:0] out_dibit
);

// Gray dibit -> phase index (binary), p = {d1, d0 ^ d1}
function [1:0] p_of_dibit;
    input [1:0] d;
    p_of_dibit = {d[1], d[0] ^ d[1]};
endfunction

// phase index (binary) -> Gray dibit, d = {p1, p0 ^ p1}
function [1:0] dibit_of_p;
    input [1:0] p;
    dibit_of_p = {p[1], p[0] ^ p[1]};
endfunction

reg [1:0] p_prev;

wire [1:0] p_now  = p_of_dibit(in_dibit);
wire [1:0] p_diff = p_now - p_prev;              // 2-bit subtract = (p_now - p_prev) mod 4

always @(posedge clk) begin
    if (rst) begin
        out_valid <= 1'b0;
        out_dibit <= 2'b00;
        p_prev    <= 2'b00;
    end else begin
        out_valid <= in_valid;
        if (in_valid) begin
            out_dibit <= enable ? dibit_of_p(p_diff) : in_dibit;
            p_prev    <= p_now;
        end
    end
end

endmodule
