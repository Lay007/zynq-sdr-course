// Issue #68: can the receiver wait for a packet that another board sends once?
//
// Board A sends one Lab 11.45 frame, then silence (noise only), cyclically; board B starts the
// fabric receiver at an arbitrary moment. This bench feeds qpsk_zynq_ber_top (gpreg bridge
// parameters, Lab 11.45 mode) from such a stream and starts BURSTS receptions at pseudo-random
// points. With LISTEN = 0 the receive window is the frame + 256 symbols after start; with
// LISTEN = 1 the receiver waits up to 65535 symbols. Each reception runs until done or timeout.
//
// Input: tmp/listen/<FILE> from gen_qpsk_burst_stream.py (NS samples, read cyclically).
// Defines: LISTEN (0/1), FILE, NS, BURSTS, MAX_FEED. Diagnostics: DIAG (loop state every 4096
// samples), PKTDIAG with PERIOD (per packet of the stream: detector, decisions passed, best
// preamble match), REWIND_TEST (experiment: reset the loops whenever the detector drops).
`timescale 1ns/1ps

`ifndef LISTEN
`define LISTEN 1
`endif
`ifndef FILE
`define FILE "qpsk_burst_gap19.mem"
`endif
`ifndef NS
`define NS 97280
`endif
`ifndef BURSTS
`define BURSTS 20
`endif

module tb_qpsk_listen;
  localparam integer W = 16, INDEX_W = 16, SYMS = 152, PRE_BITS = 48;
`ifndef MAX_FEED
`define MAX_FEED 700000   // > 65535 symbols * 8 samples: the listen window ends first
`endif
  localparam integer MAX_FEED = `MAX_FEED;

  reg clk = 1'b0;
  always #5 clk = ~clk;
  reg rst = 1'b1, start = 1'b0, rx_valid = 1'b0;
  reg signed [W-1:0] rx_i = 0, rx_q = 0;
  reg [31:0] samples [0:`NS-1];
  reg [8*64-1:0] path;
  integer pos, b, fed, seed, locked, clean, gross, bits, errs, timeouts, hung, fed_sum, wait_cycles;
  reg done_seen;

  wire busy, done, timed_out;
  wire [INDEX_W-1:0] received_symbols, total_bit_errors, payload_bit_errors;

  qpsk_zynq_ber_top #(
    .W(W), .SPS(8), .INDEX_W(INDEX_W), .MAX_FRAME_BITS(512), .PHASE_W(3), .FLUSH_SYMBOLS(16),
    .LOCK_PREAMBLE_BITS(24), .LOCK_ERR_TOL(1), .RX_SIG_THRESH(8), .RX_SAMPLE_MARGIN(256),
    .COSTAS_KP_LOG_TRACK(7), .COSTAS_ACQ_SYMBOLS(64), .COSTAS_KI_LOG(4),
    .TIMING_RECOVERY_ENABLE(1), .COARSE_ENABLE(1)
  ) dut (
    .clk(clk), .rst(rst), .start(start),
    .symbol_count(SYMS[INDEX_W-1:0]), .preamble_count(PRE_BITS[INDEX_W-1:0]),
    .start_offset(16'd0),
    .dc_block_en(1'b1), .costas_en(1'b1), .coarse_cfo_en(1'b0), .phase_pick_en(1'b1),
    .timing_recovery_en(1'b1), .costas_hold_phase(1'b0), .diff_en(1'b1), .listen_en(`LISTEN != 0), .abort_listen(1'b0), .msg_mode(1'b0), .msg_bits(256'd0),
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
  reg to_seen;
  always @(posedge clk) if (start) to_seen <= 1'b0; else if (timed_out) to_seen <= 1'b1;

`ifdef DUMPDIB
  // Every dibit that reaches the BER counter, with the reception number, for offline analysis.
  integer dib_fd;
  initial dib_fd = $fopen("tmp/listen/dibits.txt", "w");
  always @(posedge clk) if (dut.recovered_valid) $fwrite(dib_fd, "%0d %0d %0d\n", b, dut.recovered_dibit, dut.ber_counter_i.winner_valid);
`endif

`ifdef REWIND_TEST
  // Experiment: when the packet detector drops, put the loops back to their reset state.
  reg prev_present = 1'b0;
  always @(posedge clk) begin
    prev_present <= dut.rx_chain_i.pkt_present;
    if (prev_present && !dut.rx_chain_i.pkt_present) begin
      dut.rx_chain_i.costas_i.theta = 0;
      dut.rx_chain_i.costas_i.freq = 0;
      dut.rx_chain_i.g_qpsk_timing_recovery.continuous_timing_i.integ = 0;
      dut.rx_chain_i.g_qpsk_timing_recovery.continuous_timing_i.w_step = 16384;
    end
  end
`endif

`ifdef PKTDIAG
  // Per packet of the stream (PERIOD samples, frame first): what the receiver did with it.
  integer pk_pres = 0, pk_rec = 0, pk_sym = 0, pk_pos;
  integer pk_best = 0, mm;
  always @(posedge clk) begin
    if (rx_valid) begin
      pk_pos = (pos + `NS - 1) % `NS % `PERIOD;
      if (pk_pos == 0) begin
        $display("  pkt start: present=%0d costas_freq=%0d w_step=%0d integ=%0d long=%0d",
                 dut.rx_chain_i.pkt_present, dut.rx_chain_i.costas_i.freq,
                 dut.rx_chain_i.g_qpsk_timing_recovery.continuous_timing_i.w_step,
                 dut.rx_chain_i.g_qpsk_timing_recovery.continuous_timing_i.integ,
                 dut.rx_chain_i.packet_detect_i.long_mean);
        pk_pres = 0; pk_rec = 0; pk_sym = 0; pk_best = 0;
      end
      if (pk_pos == 2 * 152 * 8)
        $display("  pkt end: present %0d/%0d symbols, decisions passed %0d, best preamble match %0d/24, locked=%0d busy=%0d",
                 pk_pres, pk_sym, pk_rec, pk_best, dut.ber_counter_i.winner_valid, busy);
    end
    if (dut.rx_chain_i.debug_symbol_valid) begin
      pk_sym = pk_sym + 1;
      if (dut.rx_chain_i.pkt_present) pk_pres = pk_pres + 1;
    end
    if (dut.recovered_valid) pk_rec = pk_rec + 1;
    if (dut.ber_counter_i.bit_ber_a.in_valid) begin
      mm = dut.ber_counter_i.bit_ber_a.m_noninv; if (mm > pk_best) pk_best = mm;
      mm = dut.ber_counter_i.bit_ber_a.m_inv;    if (mm > pk_best) pk_best = mm;
      mm = dut.ber_counter_i.bit_ber_b.m_noninv; if (mm > pk_best) pk_best = mm;
      mm = dut.ber_counter_i.bit_ber_b.m_inv;    if (mm > pk_best) pk_best = mm;
    end
  end
`endif

`ifdef DIAG
  // Loop state every 4096 input samples: how often the Costas gate passes (signal or noise above
  // RX_SIG_THRESH), the Costas frequency integrator, the Gardner step and integrator.
  integer d_sym = 0, d_run = 0, d_n = 0;
  always @(posedge clk) begin
    if (dut.rx_chain_i.costas_i.in_valid) begin
      d_sym = d_sym + 1;
      if (dut.rx_chain_i.costas_i.loop_run) d_run = d_run + 1;
    end
    if (rx_valid) begin
      d_n = d_n + 1;
      if (d_n % 4096 == 0) begin
        $display("  diag n=%0d gate %0d/%0d present=%0d sig_seen=%0d costas_freq=%0d w_step=%0d integ=%0d",
                 d_n, d_run, d_sym, dut.rx_chain_i.pkt_present, dut.rx_chain_i.sig_seen, dut.rx_chain_i.costas_i.freq,
                 dut.rx_chain_i.g_qpsk_timing_recovery.continuous_timing_i.w_step,
                 dut.rx_chain_i.g_qpsk_timing_recovery.continuous_timing_i.integ);
        d_sym = 0; d_run = 0;
      end
    end
  end
`endif

  initial begin
    $sformat(path, "tmp/listen/%0s", `FILE);
    $readmemh(path, samples);
    seed = 68; pos = 0; hung = 0; locked = 0; clean = 0; gross = 0; bits = 0; errs = 0;
    timeouts = 0; fed_sum = 0; done_seen = 1'b0;
    repeat (5) @(posedge clk);
    rst = 1'b0;
    for (b = 0; b < `BURSTS; b = b + 1) begin
      pos = (pos + ($unsigned($random(seed)) % `NS)) % `NS;   // the host starts at an arbitrary point
      repeat (3) @(negedge clk);
      while (busy) @(negedge clk);
      start = 1'b1;
      @(negedge clk) start = 1'b0;
      fed = 0;
      while (!done_seen && fed < MAX_FEED) begin
        rx_valid = 1'b1;
        rx_i = samples[pos][31:16];
        rx_q = samples[pos][15:0];
        pos = (pos + 1) % `NS;
        fed = fed + 1;
        @(negedge clk);
      end
      rx_valid = 1'b0;
      wait_cycles = 0;
      while (!done_seen && wait_cycles < 20000) begin @(negedge clk); wait_cycles = wait_cycles + 1; end
      if (!done_seen) begin
        hung = hung + 1;
        $display("burst %0d: no done or timeout (busy=%0d)", b, busy);
      end
      fed_sum = fed_sum + fed;
      if (to_seen) timeouts = timeouts + 1;
`ifdef VERBOSE
      $display("burst %0d fed %0d received %0d err %0d timed_out %0d", b, fed, received_symbols, payload_bit_errors, to_seen);
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
    $display("RESULT file=%0s listen=%0d bursts=%0d locked=%0d clean=%0d gross=%0d payload_errors=%0d/%0d timeouts=%0d hung=%0d mean_fed=%0d",
             `FILE, `LISTEN, `BURSTS, locked, clean, gross, errs, bits, timeouts, hung, fed_sum / `BURSTS);
    $finish;
  end
endmodule
