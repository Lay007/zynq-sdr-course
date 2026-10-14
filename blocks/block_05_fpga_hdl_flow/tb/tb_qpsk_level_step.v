// Issue #58 follow-up: a 20 dB level step in the middle of a frame, through the receiver that runs
// on the board (qpsk_zynq_ber_top with the parameters of the gpreg bridge, Lab 11.45 mode:
// DC blocker, Costas in differential track mode, Gardner timing loop, differential decoding).
//
// On two boards a sudden 20 dB DROP mid-frame lost the rest of that frame while the same RISE did
// not (reports/hardware/ad9361-agc-frame-step-20261014.md). The suspect is the DC blocker: it is a
// running mean from the frame start, so after the drop it still subtracts an offset learned on the
// strong signal (mostly the preamble, whose differential symbols repeat), which is comparable to
// the weak signal for the rest of the frame.
//
// Input: tmp/level_step/qpsk_level_step_<case>.mem (run from the repository root), written by
// blocks/block_05_fpga_hdl_flow/python/gen_qpsk_level_step.py (one {I,Q} 16+16-bit word per
// sample). Define DC_EN=0 to run the same input with the DC blocker off.
`timescale 1ns/1ps

`ifndef DC_EN
`define DC_EN 1
`endif
`ifndef CASE
`define CASE "down"
`endif

module tb_qpsk_level_step;
  localparam integer W = 16, INDEX_W = 16, NS = 6000, SYMS = 152, PRE_BITS = 48;

  reg clk = 1'b0;
  always #5 clk = ~clk;
  reg rst = 1'b1, start = 1'b0, rx_valid = 1'b0;
  reg signed [W-1:0] rx_i = 0, rx_q = 0;
  reg [31:0] samples [0:NS-1];
  reg [8*64-1:0] path;
  integer n, wait_cycles, dc_samples;
  reg done_seen = 1'b0;
  always @(posedge clk) if (done) done_seen <= 1'b1;
  real dc_mag_sum;

  wire busy, done, timed_out;
  wire [INDEX_W-1:0] received_symbols, total_bit_errors, payload_bit_errors;
  wire [INDEX_W-1:0] first_err, last_err;
  wire [1:0] rotation;

  qpsk_zynq_ber_top #(
    .W(W), .SPS(8), .INDEX_W(INDEX_W), .MAX_FRAME_BITS(512), .PHASE_W(3), .FLUSH_SYMBOLS(16),
    .LOCK_PREAMBLE_BITS(24), .LOCK_ERR_TOL(1), .RX_SIG_THRESH(8), .RX_SAMPLE_MARGIN(256),
    .COSTAS_KP_LOG_TRACK(7), .COSTAS_ACQ_SYMBOLS(64), .COSTAS_KI_LOG(4),
    .TIMING_RECOVERY_ENABLE(1), .COARSE_ENABLE(1)
  ) dut (
    .clk(clk), .rst(rst), .start(start),
    .symbol_count(SYMS[INDEX_W-1:0]), .preamble_count(PRE_BITS[INDEX_W-1:0]),
    .start_offset(16'd0),
    .dc_block_en(`DC_EN), .costas_en(1'b1), .coarse_cfo_en(1'b0), .phase_pick_en(1'b1),
    .timing_recovery_en(1'b1), .costas_hold_phase(1'b0), .diff_en(1'b1), .listen_en(1'b0),
    .busy(busy), .done(done),
    .tx_valid(), .tx_i(), .tx_q(),
    .rx_valid(rx_valid), .rx_i(rx_i), .rx_q(rx_q),
    .timed_out(timed_out),
    .received_symbols(received_symbols), .total_bit_errors(total_bit_errors),
    .payload_bit_errors(payload_bit_errors), .rotation_index(rotation),
    .payload_error_segments(), .first_payload_error_index(first_err), .last_payload_error_index(last_err),
    .debug_symbol_valid(), .debug_symbol_i(), .debug_symbol_q(),
    .debug_recovered_valid(), .debug_recovered_dibit(),
    .timing_mu(), .timing_omega(), .timing_error()
  );

  // DC blocker estimate seen at the matched-filter input, averaged over the last part of the
  // frame (samples 1200..2400 of the input, after the step).
  wire signed [W-1:0] dc_est_i = dut.rx_chain_i.dc_blocker_i.dc_i;
  wire signed [W-1:0] dc_est_q = dut.rx_chain_i.dc_blocker_i.dc_q;

  initial begin
    $sformat(path, "tmp/level_step/qpsk_level_step_%0s.mem", `CASE);
    $readmemh(path, samples);
    dc_mag_sum = 0.0;
    dc_samples = 0;
    repeat (5) @(posedge clk);
    rst = 1'b0;
    repeat (5) @(posedge clk);
    @(negedge clk) start = 1'b1;
    @(negedge clk) start = 1'b0;
    for (n = 0; n < NS; n = n + 1) begin
      @(negedge clk);
      rx_valid = 1'b1;
      rx_i = samples[n][31:16];
      rx_q = samples[n][15:0];
      if (n >= 1200 && n < 2400) begin
        dc_mag_sum = dc_mag_sum + $sqrt(1.0 * dc_est_i * dc_est_i + 1.0 * dc_est_q * dc_est_q);
        dc_samples = dc_samples + 1;
      end
      if (done_seen) n = NS;
    end
    @(negedge clk) rx_valid = 1'b0;
    wait_cycles = 0;
    while (!done_seen && !timed_out && wait_cycles < 20000) begin
      @(posedge clk);
      wait_cycles = wait_cycles + 1;
    end
    $display("RESULT case=%0s dc_en=%0d received=%0d total_errors=%0d payload_errors=%0d first=%0d last=%0d mean_dc=%0.1f timed_out=%0d",
             `CASE, `DC_EN, received_symbols, total_bit_errors, payload_bit_errors, first_err, last_err,
             dc_samples ? dc_mag_sum / dc_samples : 0.0, timed_out);
    $finish;
  end
endmodule
