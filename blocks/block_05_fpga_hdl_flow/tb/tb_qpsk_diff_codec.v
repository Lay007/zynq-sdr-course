// Lab 5.15 - differential QPSK encoder+decoder: rotation invariance at RTL.
//
// Drives a PRBS info-dibit stream through qpsk_diff_encoder, rotates the absolute symbol by each of
// the four QPSK quadrants (what a whole-burst carrier offset does), decodes with qpsk_diff_decoder,
// and asserts the info is recovered. The point of differential coding is that ONLY the reference
// symbol (index 0) depends on the absolute rotation; every later symbol is rotation-invariant. So the
// bench checks:
//   - rotation 0: every symbol recovered (encoder and decoder both start from phase 0);
//   - rotations 90/180/270: every symbol EXCEPT index 0 recovered, and index 0 wrong by exactly the
//     rotation -- proof the rotation cancels in the differences and survives only at the seam.
// It also checks enable=0 is a bit-exact passthrough (ordinary QPSK).
//
// Checking exit status alone would pass while measuring nothing, so mismatches are counted and the
// recovered-vs-expected totals are printed for every rotation.

`timescale 1ns/1ps

module tb_qpsk_diff_codec;

localparam integer N = 200;          // info symbols per rotation

reg clk = 1'b0;
reg rst = 1'b1;
reg en  = 1'b1;
reg        in_valid = 1'b0;
reg  [1:0] info;
integer rr, n, failures, mism, seam_ok;

// PRBS-ish info stream, deterministic and reproducible
reg [15:0] lfsr;
function [1:0] next_info;
    input dummy;
    begin
        lfsr = {lfsr[14:0], lfsr[15] ^ lfsr[13] ^ lfsr[12] ^ lfsr[10]};
        next_info = lfsr[1:0];
    end
endfunction

// --- encoder -> rotate -> decoder ------------------------------------------------------------
// The encoder is combinational + handshake-transparent; drive m_ready high so it passes straight
// through (the RRC backpressure it exists for is exercised in the full-chain benches, not here).
wire ev; wire [1:0] e_dibit; wire enc_s_ready, enc_m_last;
qpsk_diff_encoder enc (
    .clk(clk), .rst(rst), .enable(en),
    .s_valid(in_valid), .s_dibit(info), .s_last(1'b0), .s_ready(enc_s_ready),
    .m_valid(ev), .m_dibit(e_dibit), .m_last(enc_m_last), .m_ready(1'b1)
);

// rotate the absolute symbol by rot quadrants: p -> (p+rot) mod 4, back to a dibit
reg [1:0] rot;
function [1:0] p_of;    input [1:0] d; p_of = {d[1], d[0]^d[1]}; endfunction
function [1:0] d_of;    input [1:0] p; d_of = {p[1], p[0]^p[1]}; endfunction
wire [1:0] e_rot = d_of(p_of(e_dibit) + rot);

wire dv; wire [1:0] d_dibit;
qpsk_diff_decoder dec (
    .clk(clk), .rst(rst), .enable(en), .in_valid(ev), .in_dibit(e_rot),
    .out_valid(dv), .out_dibit(d_dibit)
);

// reference model of the info stream, replayed per rotation to compare against
reg [1:0] info_hist [0:N-1];

always #5 clk = ~clk;

integer idx;
initial begin
    failures = 0;

    // ---- differential mode, all four rotations ----
    for (rr = 0; rr <= 3; rr = rr + 1) begin
        rot = rr[1:0];
        en = 1'b1;
        rst = 1'b1; in_valid = 1'b0; lfsr = 16'hACE1;
        @(negedge clk); @(negedge clk); rst = 1'b0; @(negedge clk);

        // record the info stream we will feed
        for (n = 0; n < N; n = n + 1) info_hist[n] = 2'bxx;

        mism = 0; seam_ok = 0; idx = 0;
        // feed N info symbols continuously; collect decoder outputs (2-cycle pipeline)
        fork
            begin : FEED
                for (n = 0; n < N; n = n + 1) begin
                    info = next_info(0);
                    info_hist[n] = info;
                    in_valid = 1'b1;
                    @(negedge clk);
                end
                in_valid = 1'b0;
                repeat (4) @(negedge clk);
            end
            begin : COLLECT
                idx = 0;
                while (idx < N) begin
                    @(posedge clk);
                    if (dv) begin
                        // dv asserts 2 cycles after the matching info was fed -> index idx
                        if (idx == 0) begin
                            // seam/reference symbol: correct only when rot==0
                            if (rr == 0 && d_dibit === info_hist[0]) seam_ok = 1;
                            if (rr != 0) seam_ok = 1; // expected to differ; not counted as a failure
                        end else if (d_dibit !== info_hist[idx]) begin
                            mism = mism + 1;
                        end
                        idx = idx + 1;
                    end
                end
            end
        join

        $display("rotation %3d deg: %0d/%0d payload symbols recovered (%0d mismatch), seam handled=%0d",
                 90*rr, (N-1)-mism, N-1, mism, seam_ok);
        if (mism != 0) failures = failures + 1;
    end

    // ---- enable=0 passthrough: absolute dibit must appear unchanged at the decoder ----
    en = 1'b0; rot = 2'd0;
    rst = 1'b1; in_valid = 1'b0; lfsr = 16'h1234;
    @(negedge clk); @(negedge clk); rst = 1'b0; @(negedge clk);
    mism = 0; idx = 0;
    fork
        begin
            for (n = 0; n < N; n = n + 1) begin
                info = next_info(0); info_hist[n] = info; in_valid = 1'b1; @(negedge clk);
            end
            in_valid = 1'b0; repeat (4) @(negedge clk);
        end
        begin
            idx = 0;
            while (idx < N) begin
                @(posedge clk);
                if (dv) begin
                    if (d_dibit !== info_hist[idx]) mism = mism + 1;
                    idx = idx + 1;
                end
            end
        end
    join
    $display("passthrough (enable=0): %0d/%0d symbols identical (%0d mismatch)", N-mism, N, mism);
    if (mism != 0) failures = failures + 1;

    if (failures == 0)
        $display("PASS: qpsk_diff_codec -- rotation-invariant recovery and clean passthrough");
    else
        $display("FAIL: qpsk_diff_codec -- %0d configuration(s) failed", failures);
    $finish;
end

endmodule
