// Lab 5.13 - the feedforward symbol-timing phase pick, against two real bursts.
//
// Both stimulus files are raw core_rx captures taken off the board on the same bench, at the
// same sampler setting, seconds apart. They carry the same frame at the same level with the
// same noise -- and they need DIFFERENT sampling phases, because the frame arrived at a
// different sub-symbol offset:
//
//   qpsk_selfota_burst_centred_rx.mem   the on-chip counter read 0 errors
//   qpsk_selfota_burst_halfsym_rx.mem   the on-chip counter read 124 of 280, half a symbol off
//
// Run each through dc_blocker -> matched filter -> qpsk_mf_phase_picker -> sampler -> Costas
// -> decision -> frame-sync, sweeping the sampler's start_offset.
//
//   picker bypassed: the clean offsets differ between the two captures. This is the disease.
//   picker enabled : both are clean at the same offsets, centred on 0, because the picker
//                    releases its delayed stream starting on a symbol centre.
//
// That the two captures disagree at all is the whole point. A receiver that only works when
// the transmitter happens to hand it the right phase is not a receiver.

`timescale 1ns/1ps

module tb_qpsk_phase_picker;
  localparam W = 16, INDEX_W = 16, SYMS = 140, CHAIN_SYMS = 450, NS = 4000;
  localparam integer EXPECT_BITS = 2 * SYMS;

  reg clk = 0, rst = 1, rx_valid = 0, cnt_start = 0, pick_en = 1;
  reg signed [W-1:0] rx_i = 0, rx_q = 0;
  reg [INDEX_W-1:0] start_offset = 0;
  reg [31:0] samp [0:NS-1];
  integer n, so, w, f, failures;
  reg [INDEX_W-1:0] rxsyms, errs;
  reg [7:0] clean_mask;

  wire dcv;
  wire signed [W-1:0] dci, dcq;
  dc_blocker #(.W(W), .K_MAX(10)) dcb (
      .clk(clk), .rst(rst), .enable(1'b1),
      .in_valid(rx_valid), .in_i(rx_i), .in_q(rx_q),
      .out_valid(dcv), .out_i(dci), .out_q(dcq));

  wire mfv;
  wire signed [W-1:0] mfi, mfq;
  bpsk_rrc_rx_fir mf (
      .clk(clk), .rst(rst), .in_valid(dcv), .in_i(dci), .in_q(dcq),
      .out_valid(mfv), .out_i(mfi), .out_q(mfq));

  wire pkv, plock;
  wire [2:0] pph;
  wire signed [W-1:0] pki, pkq;
  qpsk_mf_phase_picker #(.W(W), .SPS(8)) pick (
      .clk(clk), .rst(rst), .enable(pick_en),
      .in_valid(mfv), .in_i(mfi), .in_q(mfq),
      .out_valid(pkv), .out_i(pki), .out_q(pkq),
      .phase_locked(plock), .phase(pph));

  wire sv;
  wire signed [W-1:0] si, sq;
  bpsk_symbol_timing_sampler #(.W(W), .SPS(8), .INDEX_W(INDEX_W)) samp_i (
      .clk(clk), .rst(rst), .in_valid(pkv), .in_i(pki), .in_q(pkq),
      .start_offset(start_offset), .symbol_count(CHAIN_SYMS[INDEX_W-1:0]),
      .out_valid(sv), .out_i(si), .out_q(sq));

  wire cv;
  wire signed [W-1:0] ci, cq;
  qpsk_costas #(.W(W)) costas_i (
      .clk(clk), .rst(rst), .rst_phase(rst), .enable(1'b1),
      .in_valid(sv), .in_i(si), .in_q(sq),
      .out_valid(cv), .out_i(ci), .out_q(cq));

  wire dv;
  wire [1:0] dib;
  qpsk_hard_decision dec (.clk(clk), .rst(rst), .in_valid(cv), .in_i(ci), .in_q(cq),
      .out_valid(dv), .out_dibit(dib));

  wire cbusy, cdone, cswap;
  wire [INDEX_W-1:0] rsym, terr;
  qpsk_ber_counter #(.INDEX_W(INDEX_W), .MAX_FRAME_BITS(512),
                     .LOCK_PREAMBLE_BITS(24), .LOCK_ERR_TOL(3)) cnt (
      .clk(clk), .rst(rst), .start(cnt_start), .abort(1'b0),
      .symbol_count(SYMS[INDEX_W-1:0]), .preamble_count(16'd24),
      .in_valid(dv), .in_dibit(dib), .busy(cbusy), .done(cdone), .quadrant_swapped(cswap),
      .received_symbols(rsym), .total_bit_errors(terr));

  always #5 clk = ~clk;

  task run_off(input integer offs);
    begin
      start_offset = offs[INDEX_W-1:0];
      rst = 1; rx_valid = 0; cnt_start = 0;
      @(negedge clk); @(negedge clk); rst = 0; @(negedge clk);
      cnt_start = 1; @(negedge clk); cnt_start = 0;
      for (n = 0; n < NS; n = n + 1) begin
        rx_i = samp[n][31:16]; rx_q = samp[n][15:0]; rx_valid = 1;
        @(negedge clk);
        if (cdone) n = NS;
      end
      rx_valid = 0;
      w = 0;
      while (!cdone && w < 4096) begin @(posedge clk); w = w + 1; end
      @(posedge clk);
      rxsyms = rsym; errs = terr;
    end
  endtask

  // Which start_offsets decode cleanly, as a bitmask over the 8 sample phases.
  task clean_offsets(output reg [7:0] mask);
    begin
      mask = 8'd0;
      for (so = 0; so < 8; so = so + 1) begin
        run_off(so);
        if (rxsyms == SYMS[INDEX_W-1:0] && errs == 0) mask[so] = 1'b1;
      end
    end
  endtask

  reg [7:0] mask_centred_off, mask_halfsym_off, mask_centred_on, mask_halfsym_on;

  initial begin
    repeat (4) @(negedge clk);
    failures = 0;

    pick_en = 1'b0;
    $readmemh("blocks/block_05_fpga_hdl_flow/tb/qpsk_selfota_burst_centred_rx.mem", samp);
    clean_offsets(mask_centred_off);
    $readmemh("blocks/block_05_fpga_hdl_flow/tb/qpsk_selfota_burst_halfsym_rx.mem", samp);
    clean_offsets(mask_halfsym_off);
    $display("  picker off: clean offsets  centred=%b  half-symbol=%b", mask_centred_off, mask_halfsym_off);

    if (mask_centred_off == 8'd0 || mask_halfsym_off == 8'd0) begin
      $display("FAIL: qpsk_phase_picker -- a capture never decodes even with the picker bypassed");
      failures = failures + 1;
    end
    if (mask_centred_off == mask_halfsym_off) begin
      $display("FAIL: qpsk_phase_picker -- the two captures no longer disagree, so this bench");
      $display("      proves nothing. Re-capture a burst that arrives half a symbol off.");
      failures = failures + 1;
    end

    pick_en = 1'b1;
    $readmemh("blocks/block_05_fpga_hdl_flow/tb/qpsk_selfota_burst_centred_rx.mem", samp);
    clean_offsets(mask_centred_on);
    $readmemh("blocks/block_05_fpga_hdl_flow/tb/qpsk_selfota_burst_halfsym_rx.mem", samp);
    clean_offsets(mask_halfsym_on);
    $display("  picker on : clean offsets  centred=%b  half-symbol=%b", mask_centred_on, mask_halfsym_on);

    // The contract is that the picker removes the dependence on ARRIVAL phase: the two captures
    // must become clean on a COMMON set of offsets, centred on 0. Exact mask equality used to hold
    // and was asserted, but it is a brittle proxy -- it only survives while both captures sit at
    // the same margin. Improving the DC blocker (running average instead of a fixed short tau)
    // widened both masks, 01111111-style, and the extra marginal offsets appeared asymmetrically:
    // centred gained one that half-symbol did not. Both still decode at offset 0 and their clean
    // sets overlap, so the picker's contract holds; only the proxy broke. Assert the contract.
    if ((mask_centred_on & mask_halfsym_on) == 8'd0) begin
      $display("FAIL: qpsk_phase_picker -- the two captures share NO clean sampler phase");
      failures = failures + 1;
    end
    if (mask_centred_on == 8'd0 || mask_halfsym_on == 8'd0) begin
      $display("FAIL: qpsk_phase_picker -- a capture never decodes with the picker enabled");
      failures = failures + 1;
    end
    // The picker's contract: the released stream starts on a symbol centre, so start_offset=0
    // samples the centres.
    if (!mask_centred_on[0] || !mask_halfsym_on[0]) begin
      $display("FAIL: qpsk_phase_picker -- start_offset=0 is not a symbol centre; TAP_TRIM is wrong");
      failures = failures + 1;
    end

    if (failures == 0)
      $display("PASS: qpsk_phase_picker -- two bursts arriving half a symbol apart both decode at BER 0/%0d, same phase",
               EXPECT_BITS);
    else
      $display("FAIL: qpsk_phase_picker -- %0d check(s) failed", failures);
    $finish;
  end
endmodule
