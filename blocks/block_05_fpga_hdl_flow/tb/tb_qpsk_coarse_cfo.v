// Lab 5.14 - feedforward coarse CFO estimator, end to end.
//
// Two boards with independent references put the carrier tens of kHz off, which a Costas loop
// (few-hundred-Hz pull-in) cannot acquire. qpsk_coarse_cfo estimates the offset from the
// differential 4th power over a window, removes it with an NCO, and hands the Costas a
// trackable residual. This bench drives framed QPSK bursts (real preamble+payload from the
// frame ROM) carrying a large CFO through
//   qpsk_coarse_cfo -> qpsk_costas -> qpsk_hard_decision -> qpsk_ber_counter
// and asserts three things on committed, hardware-scale stimulus:
//   * a 25 kHz offset BREAKS the frame when the estimator is bypassed (the offset is real);
//   * the estimator removes it and the frame decodes at BER 0;
//   * a near-zero-offset burst also decodes (the estimator does no harm at 0).
//
// Symbols are fed sparsely (one per 4 cycles), exactly as the real SPS=8 sampler delivers them
// -- the counter's dibit->2-bit flatten needs the idle cycles.

`timescale 1ns/1ps

module tb_qpsk_coarse_cfo;
  localparam W = 16, INDEX_W = 16, SYMS = 140, NS = 512;
  localparam integer EXPECT_BITS = 2 * SYMS;

  reg clk = 0, rst = 1, vld = 0, cnt_start = 0, cfo_en = 1;
  reg signed [W-1:0] ii = 0, qq = 0;
  reg [31:0] samp [0:NS-1];
  integer n, w, failures;
  reg [INDEX_W-1:0] got_recv, got_err;
  reg signed [23:0] got_omega;

  wire cvo, crdy;
  wire signed [W-1:0] ci, cq;
  wire signed [23:0] omega;
  qpsk_coarse_cfo #(.W(W), .WIN_SYMBOLS(64), .SQ_SHIFT(11), .SIG_THRESH(1000)) cfo (
      .clk(clk), .rst(rst), .enable(cfo_en),
      .in_valid(vld), .in_i(ii), .in_q(qq),
      .out_valid(cvo), .out_i(ci), .out_q(cq), .cfo_ready(crdy), .cfo_omega(omega));

  wire svo;
  wire signed [W-1:0] si, sq;
  qpsk_costas #(.W(W)) costas_i (
      .clk(clk), .rst(rst), .rst_phase(rst), .enable(1'b1),
      .in_valid(cvo), .in_i(ci), .in_q(cq),
      .out_valid(svo), .out_i(si), .out_q(sq));

  wire dvo;
  wire [1:0] dib;
  qpsk_hard_decision dec (.clk(clk), .rst(rst), .in_valid(svo), .in_i(si), .in_q(sq),
      .out_valid(dvo), .out_dibit(dib));

  wire cbusy, cdone, cswap;
  wire [INDEX_W-1:0] rsym, terr;
  qpsk_ber_counter #(.INDEX_W(INDEX_W), .MAX_FRAME_BITS(512),
                     .LOCK_PREAMBLE_BITS(24), .LOCK_ERR_TOL(3)) cnt (
      .clk(clk), .rst(rst), .start(cnt_start), .abort(1'b0),
      .symbol_count(SYMS[INDEX_W-1:0]), .preamble_count(16'd24),
      .in_valid(dvo), .in_dibit(dib), .busy(cbusy), .done(cdone), .quadrant_swapped(cswap),
      .received_symbols(rsym), .total_bit_errors(terr));

  always #5 clk = ~clk;

  task run(input en);
    begin
      cfo_en = en;
      rst = 1; vld = 0; cnt_start = 0;
      repeat (4) @(negedge clk); rst = 0; @(negedge clk);
      cnt_start = 1; @(negedge clk); cnt_start = 0;
      // frame + flush (WIN-deep delay line), one symbol every 4 cycles
      for (n = 0; n < 240; n = n + 1) begin
        ii = samp[n][31:16]; qq = samp[n][15:0]; vld = 1; @(negedge clk);
        vld = 0; ii = 0; qq = 0; @(negedge clk); @(negedge clk); @(negedge clk);
        if (cdone) n = 240;
      end
      w = 0; while (!cdone && w < 8192) begin @(posedge clk); w = w + 1; end
      @(posedge clk);
      got_recv = rsym; got_err = terr; got_omega = omega;
    end
  endtask

  initial begin
    failures = 0;

    // 1) 25 kHz offset, estimator bypassed -> must break
    $readmemh("blocks/block_05_fpga_hdl_flow/tb/framed_cfo25k_rx.mem", samp);
    run(1'b0);
    $display("  CFO 25kHz, estimator OFF: recv=%0d errors=%0d/280 omega=%0d", got_recv, got_err, got_omega);
    if (got_recv == SYMS[INDEX_W-1:0] && got_err <= 20) begin
      $display("FAIL: a 25 kHz offset decoded without correction -- the test proves nothing"); failures = failures + 1;
    end

    // 2) 25 kHz offset, estimator on -> must decode BER 0, and omega must be a real ~25 kHz estimate
    run(1'b1);
    $display("  CFO 25kHz, estimator ON:  recv=%0d errors=%0d/280 omega=%0d", got_recv, got_err, got_omega);
    if (got_recv != SYMS[INDEX_W-1:0] || got_err != 0) begin
      $display("FAIL: coarse CFO did not recover the 25 kHz frame"); failures = failures + 1;
    end
    if (got_omega < 700000 || got_omega > 1000000) begin
      $display("FAIL: omega %0d is not a plausible +25 kHz estimate", got_omega); failures = failures + 1;
    end

    // 3) near-zero offset, estimator on -> must still decode (does no harm)
    $readmemh("blocks/block_05_fpga_hdl_flow/tb/framed_cfo0_rx.mem", samp);
    run(1'b1);
    $display("  CFO ~0,     estimator ON:  recv=%0d errors=%0d/280 omega=%0d", got_recv, got_err, got_omega);
    if (got_recv != SYMS[INDEX_W-1:0] || got_err != 0) begin
      $display("FAIL: coarse CFO harmed a zero-offset frame"); failures = failures + 1;
    end

    if (failures == 0)
      $display("PASS: qpsk_coarse_cfo -- removes a 25 kHz offset the Costas cannot, decodes BER 0/%0d", EXPECT_BITS);
    else
      $display("FAIL: qpsk_coarse_cfo -- %0d check(s) failed", failures);
    $finish;
  end
endmodule
