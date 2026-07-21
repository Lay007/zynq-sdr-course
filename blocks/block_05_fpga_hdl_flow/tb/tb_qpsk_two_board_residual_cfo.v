// Lab 5.15 / Lab 11.33 - residual-CFO pull-in on a real two-board capture.
//
// The input is the exact core_rx BRAM stream from a 30 kHz conducted two-board run.
// The feedforward coarse estimator leaves a small, phase-dependent residual.  The old
// Costas integral gain cannot remove it inside the burst and returns a full but corrupt
// frame.  This bench bypasses the independently tested timing picker so the retained
// 2600-sample record isolates carrier pull-in.  The acquisition setting used by the board
// build must recover BER 0, then keep the quieter proportional tracking gain.

`timescale 1ns/1ps

module tb_qpsk_two_board_residual_cfo;
  localparam W = 16, INDEX_W = 16, NS = 2600, SYMS = 140, CHAIN_SYMS = 396;
  reg clk = 0, rst = 1, in_valid = 0, counter_start = 0;
  reg signed [W-1:0] in_i = 0, in_q = 0;
  reg [31:0] samples [0:NS-1];
  integer n, wait_count;
  reg old_done_seen = 0, tuned_done_seen = 0;

  wire old_valid, tuned_valid;
  wire [1:0] old_dibit, tuned_dibit;
  wire old_done, tuned_done;
  wire [INDEX_W-1:0] old_received, old_errors, tuned_received, tuned_errors;

  qpsk_rx_bit_recovery_chain #(
      .W(W), .SPS(8), .INDEX_W(INDEX_W),
      .COSTAS_SIG_THRESH(8), .COARSE_ENABLE(1)
  ) old_rx (
      .clk(clk), .rst(rst), .rst_carrier(rst),
      .dc_block_en(1'b1), .costas_en(1'b1), .coarse_cfo_en(1'b1), .phase_pick_en(1'b0),
      .in_valid(in_valid), .in_i(in_i), .in_q(in_q),
      .start_offset(16'd2), .symbol_count(CHAIN_SYMS[15:0]),
      .out_valid(old_valid), .out_dibit(old_dibit),
      .debug_symbol_valid(), .debug_symbol_i(), .debug_symbol_q(),
      .cfo_ready(), .cfo_omega());

  qpsk_rx_bit_recovery_chain #(
      .W(W), .SPS(8), .INDEX_W(INDEX_W),
      .COSTAS_KP_LOG_TRACK(7), .COSTAS_ACQ_SYMBOLS(64), .COSTAS_KI_LOG(4),
      .COSTAS_SIG_THRESH(8), .COARSE_ENABLE(1)
  ) tuned_rx (
      .clk(clk), .rst(rst), .rst_carrier(rst),
      .dc_block_en(1'b1), .costas_en(1'b1), .coarse_cfo_en(1'b1), .phase_pick_en(1'b0),
      .in_valid(in_valid), .in_i(in_i), .in_q(in_q),
      .start_offset(16'd2), .symbol_count(CHAIN_SYMS[15:0]),
      .out_valid(tuned_valid), .out_dibit(tuned_dibit),
      .debug_symbol_valid(), .debug_symbol_i(), .debug_symbol_q(),
      .cfo_ready(), .cfo_omega());

  qpsk_ber_counter #(
      .INDEX_W(INDEX_W), .MAX_FRAME_BITS(512), .LOCK_PREAMBLE_BITS(24), .LOCK_ERR_TOL(3)
  ) old_counter (
      .clk(clk), .rst(rst), .start(counter_start), .abort(1'b0),
      .symbol_count(SYMS[15:0]), .preamble_count(16'd24),
      .in_valid(old_valid), .in_dibit(old_dibit), .busy(), .done(old_done),
      .received_symbols(old_received), .total_bit_errors(old_errors));

  qpsk_ber_counter #(
      .INDEX_W(INDEX_W), .MAX_FRAME_BITS(512), .LOCK_PREAMBLE_BITS(24), .LOCK_ERR_TOL(3)
  ) tuned_counter (
      .clk(clk), .rst(rst), .start(counter_start), .abort(1'b0),
      .symbol_count(SYMS[15:0]), .preamble_count(16'd24),
      .in_valid(tuned_valid), .in_dibit(tuned_dibit), .busy(), .done(tuned_done),
      .received_symbols(tuned_received), .total_bit_errors(tuned_errors));

  always #5 clk = ~clk;
  always @(posedge clk) begin
    if (rst) begin
      old_done_seen <= 0;
      tuned_done_seen <= 0;
    end else begin
      if (old_done) old_done_seen <= 1;
      if (tuned_done) tuned_done_seen <= 1;
    end
  end

  initial begin
    $readmemh("blocks/block_05_fpga_hdl_flow/tb/qpsk_two_board_residual_cfo_rx.mem", samples);
    repeat (4) @(negedge clk);
    rst = 0;
    @(negedge clk); counter_start = 1;
    @(negedge clk); counter_start = 0;

    for (n = 0; n < NS; n = n + 1) begin
      in_i = samples[n][31:16];
      in_q = samples[n][15:0];
      in_valid = 1;
      @(negedge clk);
    end
    in_valid = 0;
    wait_count = 0;
    while (!(old_done_seen && tuned_done_seen) && wait_count < 10000) begin
      @(posedge clk);
      wait_count = wait_count + 1;
    end

    $display("  original loop: recv=%0d errors=%0d/280", old_received, old_errors);
    $display("  tuned loop:    recv=%0d errors=%0d/280", tuned_received, tuned_errors);
    if (old_received == SYMS[INDEX_W-1:0] && old_errors == 0) begin
      $display("FAIL: regression capture no longer exposes the residual-CFO failure");
      $fatal(1);
    end
    if (tuned_received != SYMS[INDEX_W-1:0] || tuned_errors != 0) begin
      $display("FAIL: tuned Costas loop did not recover the real two-board capture");
      $fatal(1);
    end
    $display("PASS: tuned residual-CFO pull-in recovers the real two-board capture at BER 0/280");
    $finish;
  end
endmodule
