// Lab 5.12e - the gear-shift window must outlast the preamble.
//
// qpsk_costas widens the loop for ACQ_SYMBOLS symbols and then drops to the quiet tracking
// gain. Those symbols are counted from the moment the FREEZE GATE opens, not from the first
// frame symbol -- and the gate trips on the RRC ramp, well before the frame proper. If the
// window expires while the frame-sync is still correlating the preamble, the last preamble
// symbols are recovered on the slow loop, the constellation has not finished rotating, and
// the correlator can latch the 90-degree branch: a locked frame with ~45% bit errors.
//
// That is not hypothetical. With ACQ_SYMBOLS=16 the gate opened at symbol 15 and the
// frame-sync locked at symbol 31 -- the window ran out on exactly the cycle it was needed,
// and 8 of 40 hardware bursts came back with ~125 of 280 bit errors.
//
// So measure the distance on the real capture and require real margin.

`timescale 1ns/1ps

module tb_qpsk_costas_acq_window;
  localparam W = 16, INDEX_W = 16, SYMS = 140, CHAIN_SYMS = 450, NS = 4000;
  localparam integer MIN_MARGIN_SYMBOLS = 8;

  reg clk = 0, rst = 1, rx_valid = 0, cnt_start = 0;
  reg signed [W-1:0] rx_i = 0, rx_q = 0;
  reg [INDEX_W-1:0] start_offset = 0;
  reg [31:0] samp [0:NS-1];
  integer n, w;
  integer gate_open_sym, lock_sym, sym_cnt, needed;
  reg seen_gate, seen_lock;

  wire rxdv;
  wire [1:0] rxdibit;
  qpsk_rx_bit_recovery_chain #(.W(W), .SPS(8), .INDEX_W(INDEX_W)) rxc (
      .clk(clk), .rst(rst), .rst_carrier(rst), .dc_block_en(1'b1), .costas_en(1'b1),
      .in_valid(rx_valid), .in_i(rx_i), .in_q(rx_q),
      .start_offset(start_offset), .symbol_count(CHAIN_SYMS[INDEX_W-1:0]),
      .out_valid(rxdv), .out_dibit(rxdibit),
      .debug_symbol_valid(), .debug_symbol_i(), .debug_symbol_q());

  wire cbusy, cdone, cswap;
  wire [INDEX_W-1:0] rsym, terr;
  qpsk_ber_counter #(.INDEX_W(INDEX_W), .MAX_FRAME_BITS(512),
                     .LOCK_PREAMBLE_BITS(24), .LOCK_ERR_TOL(3)) cnt (
      .clk(clk), .rst(rst), .start(cnt_start), .abort(1'b0),
      .symbol_count(SYMS[INDEX_W-1:0]), .preamble_count(16'd24),
      .in_valid(rxdv), .in_dibit(rxdibit),
      .busy(cbusy), .done(cdone), .quadrant_swapped(cswap),
      .received_symbols(rsym), .total_bit_errors(terr));

  always #5 clk = ~clk;

  wire loop_running    = rxc.costas_i.loop_run && rxc.costas_i.in_valid && rxc.costas_i.enable;
  wire framesync_locked = cnt.bit_ber_a.lock_acquired || cnt.bit_ber_b.lock_acquired;

  always @(posedge clk) begin
    if (rst) begin
      sym_cnt <= 0; seen_gate <= 0; seen_lock <= 0;
      gate_open_sym <= -1; lock_sym <= -1;
    end else begin
      if (rxc.costas_i.in_valid) sym_cnt <= sym_cnt + 1;
      if (loop_running && !seen_gate) begin seen_gate <= 1; gate_open_sym <= sym_cnt; end
      if (framesync_locked && !seen_lock) begin seen_lock <= 1; lock_sym <= sym_cnt; end
    end
  end

  initial begin
    $readmemh("blocks/block_05_fpga_hdl_flow/tb/qpsk_selfota_fresh_rx.mem", samp);
    repeat (4) @(negedge clk);
    start_offset = 16'd1;
    rst = 1; @(negedge clk); @(negedge clk); rst = 0; @(negedge clk);
    cnt_start = 1; @(negedge clk); cnt_start = 0;
    for (n = 0; n < NS; n = n + 1) begin
      rx_i = samp[n][31:16]; rx_q = samp[n][15:0]; rx_valid = 1;
      @(negedge clk);
      if (cdone) n = NS;
    end
    rx_valid = 0;
    w = 0;
    while (!cdone && w < 4096) begin @(posedge clk); w = w + 1; end

    if (gate_open_sym < 0 || lock_sym < 0) begin
      $display("FAIL: qpsk_costas_acq_window -- gate or frame-sync never fired (gate %0d, lock %0d)",
               gate_open_sym, lock_sym);
      $fatal(1);
    end

    needed = lock_sym - gate_open_sym;
    $display("  freeze gate opens at symbol %0d, frame-sync locks at symbol %0d", gate_open_sym, lock_sym);
    $display("  wide loop needed for %0d symbols; ACQ_SYMBOLS = %0d", needed, rxc.costas_i.ACQ_SYMBOLS);

    if (rxc.costas_i.ACQ_SYMBOLS < needed + MIN_MARGIN_SYMBOLS) begin
      $display("FAIL: qpsk_costas_acq_window -- the gear shift expires %0d symbols into the preamble;",
               rxc.costas_i.ACQ_SYMBOLS - needed);
      $display("      ACQ_SYMBOLS must be at least %0d (needed %0d + %0d margin)",
               needed + MIN_MARGIN_SYMBOLS, needed, MIN_MARGIN_SYMBOLS);
      $fatal(1);
    end
    if (rsym != SYMS[INDEX_W-1:0] || terr != 0) begin
      $display("FAIL: qpsk_costas_acq_window -- recv=%0d errors=%0d/280", rsym, terr);
      $fatal(1);
    end
    $display("PASS: qpsk_costas_acq_window -- wide loop outlasts the preamble by %0d symbols (BER 0/280)",
             rxc.costas_i.ACQ_SYMBOLS - needed);
    $finish;
  end
endmodule
