// Issue #66: many receptions from one continuous stream, the way the two-board bench runs.
//
// Board A replays a cyclic buffer of Lab 11.45 frames; the host on board B starts the fabric
// receiver again and again at arbitrary points of that stream, and the receiver only gets samples
// during a reception. This bench does the same with qpsk_zynq_ber_top (gpreg bridge parameters,
// Lab 11.45 mode): BURSTS receptions, each started after a pseudo-random gap, with no global reset
// in between, so whatever the receiver keeps from one reception to the next (the DC estimate with
// DC_PERSIST = 1) is exercised as on the board.
//
// Input: tmp/level_step/qpsk_stream_<STREAM>.mem from gen_qpsk_level_step.py --stream.
// Defines: DC_EN (0/1), PERSIST (0/1), STREAM ("steady" or "saw_down").
`timescale 1ns/1ps

`ifndef DC_EN
`define DC_EN 1
`endif
`ifndef PERSIST
`define PERSIST 1
`endif
`ifndef STREAM
`define STREAM "steady"
`endif
`ifndef BURSTS
`define BURSTS 40
`endif

module tb_qpsk_dc_bursts;
  localparam integer W = 16, INDEX_W = 16, NS = 200000, SYMS = 152, PRE_BITS = 48;

  reg clk = 1'b0;
  always #5 clk = ~clk;
  reg rst = 1'b1, start = 1'b0, rx_valid = 1'b0;
  reg signed [W-1:0] rx_i = 0, rx_q = 0;
  reg [31:0] samples [0:NS-1];
  reg [8*64-1:0] path;
  integer pos, b, fed, seed, locked, clean, gross, bits, errs, wait_cycles, hung;
  reg done_seen;

  wire busy, done, timed_out;
  wire [INDEX_W-1:0] received_symbols, total_bit_errors, payload_bit_errors;

  qpsk_zynq_ber_top #(
    .W(W), .SPS(8), .INDEX_W(INDEX_W), .MAX_FRAME_BITS(512), .PHASE_W(3), .FLUSH_SYMBOLS(16),
    .LOCK_PREAMBLE_BITS(24), .LOCK_ERR_TOL(1), .RX_SIG_THRESH(8), .RX_SAMPLE_MARGIN(256),
    .COSTAS_KP_LOG_TRACK(7), .COSTAS_ACQ_SYMBOLS(64), .COSTAS_KI_LOG(4),
    .TIMING_RECOVERY_ENABLE(1), .COARSE_ENABLE(1), .DC_PERSIST(`PERSIST)
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
    .payload_bit_errors(payload_bit_errors), .rotation_index(),
    .payload_error_segments(), .first_payload_error_index(), .last_payload_error_index(),
    .debug_symbol_valid(), .debug_symbol_i(), .debug_symbol_q(),
    .debug_recovered_valid(), .debug_recovered_dibit(),
    .timing_mu(), .timing_omega(), .timing_error()
  );

  always @(posedge clk) if (start) done_seen <= 1'b0; else if (done || timed_out) done_seen <= 1'b1;

  initial begin
    $sformat(path, "tmp/level_step/qpsk_stream_%0s.mem", `STREAM);
    $readmemh(path, samples);
    seed = 66; pos = 0; hung = 0; locked = 0; clean = 0; gross = 0; bits = 0; errs = 0; done_seen = 1'b0;
    repeat (5) @(posedge clk);
    rst = 1'b0;
    for (b = 0; b < `BURSTS; b = b + 1) begin
      pos = pos + 300 + ($unsigned($random(seed)) % 2000);   // the host starts at an arbitrary point
      repeat (3) @(negedge clk);
      while (busy) @(negedge clk);   // start is ignored while the top (its TX half too) is busy
      start = 1'b1;
      @(negedge clk) start = 1'b0;
      fed = 0;
      while (!done_seen && fed < 6000 && pos < NS) begin
        rx_valid = 1'b1;
        rx_i = samples[pos][31:16];
        rx_q = samples[pos][15:0];
        pos = pos + 1;
        fed = fed + 1;
        @(negedge clk);
      end
      rx_valid = 1'b0;
      wait_cycles = 0;
      while (!done_seen && wait_cycles < 20000) begin @(negedge clk); wait_cycles = wait_cycles + 1; end
      if (!done_seen) begin
        hung = hung + 1;
        $display("burst %0d: no done within 20000 clocks (busy=%0d)", b, busy);
      end
`ifdef VERBOSE
      $display("burst %0d pos %0d fed %0d received %0d err %0d timed_out %0d", b, pos, fed, received_symbols, payload_bit_errors, timed_out);
      $fflush();
`endif
      if (received_symbols == SYMS) begin
        locked = locked + 1;
        bits = bits + 256;
        errs = errs + payload_bit_errors;
        if (payload_bit_errors == 0) clean = clean + 1;
        if (payload_bit_errors > 8) gross = gross + 1;
      end
    end
    $display("RESULT stream=%0s dc_en=%0d persist=%0d bursts=%0d locked=%0d clean=%0d gross=%0d payload_errors=%0d/%0d hung=%0d",
             `STREAM, `DC_EN, `PERSIST, `BURSTS, locked, clean, gross, errs, bits, hung);
    $finish;
  end
endmodule
