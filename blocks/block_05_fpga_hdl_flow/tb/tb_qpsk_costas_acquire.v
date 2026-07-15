// Lab 5.12c - Costas PULL-IN TIME against the preamble length.
//
// In burst mode the loop restarts on every frame, so what matters is not steady-state
// tracking but whether it settles before the 12-symbol preamble is over. The Costas
// removes carrier phase modulo 90 degrees, so the pull-in it must perform is the path
// phase folded into [-45, +45] degrees -- and the worst case is the fold boundary.
//
// This bench rotates the REAL self-OTA capture by a range of angles (Q15 cos/sin) and
// requires the full chain to frame-lock and decode at BER=0 at every one of them.
//
// With COSTAS_KP_LOG=6 the loop corrects only ~4% of the phase error per symbol (~27
// symbol time constant): angles up to ~60 degrees still decode, but near the worst case
// the preamble is still rotating when the frame-sync correlates it, and the frame either
// fails to lock or -- worse, once the quadrant-resolving dual-branch frame-sync exists --
// locks onto a rotating preamble and delivers a ~45%-error frame. Hardware saw exactly
// that. KP_LOG=8 acquires every angle inside the preamble.

`timescale 1ns/1ps

module tb_qpsk_costas_acquire;
  localparam W = 16, INDEX_W = 16, SYMS = 140, CHAIN_SYMS = 450, NS = 4000;
  localparam integer EXPECT_BITS = 2 * SYMS;
  localparam integer NANG = 4;

  reg clk = 0, rst = 1, rx_valid = 0, cnt_start = 0;
  reg signed [W-1:0] rx_i = 0, rx_q = 0;
  reg signed [31:0] raw_i, raw_q, rot_i, rot_q;
  reg signed [31:0] cq, sq;
  reg [INDEX_W-1:0] start_offset = 0;
  reg [31:0] samp [0:NS-1];
  integer n, so, w, a, deg;
  integer best_err, best_so, locks, failures;
  reg [INDEX_W-1:0] rxsyms, errs;

  wire rxdv;
  wire [1:0] rxdibit;
  qpsk_rx_bit_recovery_chain #(.W(W), .SPS(8), .INDEX_W(INDEX_W)) rxc (
      .clk(clk), .rst(rst), .rst_carrier(rst), .dc_block_en(1'b1), .costas_en(1'b1),
      .phase_pick_en(1'b0),
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

  // Q15 cos/sin for the swept angles: 0, 30, 60, 80 degrees. 80 is the killer -- folded
  // modulo 90 it puts the residual phase error right at the pull-in worst case.
  task set_angle(input integer idx);
    begin
      case (idx)
        0: begin deg =  0; cq = 32767; sq =     0; end
        1: begin deg = 30; cq = 28378; sq = 16384; end
        2: begin deg = 60; cq = 16384; sq = 28378; end
        default: begin deg = 80; cq = 5690; sq = 32270; end
      endcase
    end
  endtask

  task run_off(input integer offs);
    begin
      start_offset = offs[INDEX_W-1:0];
      rst = 1; rx_valid = 0; cnt_start = 0;
      @(negedge clk); @(negedge clk); rst = 0; @(negedge clk);
      cnt_start = 1; @(negedge clk); cnt_start = 0;
      for (n = 0; n < NS; n = n + 1) begin
        raw_i = $signed(samp[n][31:16]);
        raw_q = $signed(samp[n][15:0]);
        rot_i = (raw_i * cq - raw_q * sq) >>> 15;
        rot_q = (raw_i * sq + raw_q * cq) >>> 15;
        rx_i = rot_i[W-1:0];
        rx_q = rot_q[W-1:0];
        rx_valid = 1;
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

  initial begin
    $readmemh("blocks/block_05_fpga_hdl_flow/tb/qpsk_selfota_fresh_rx.mem", samp);
    repeat (4) @(negedge clk);
    failures = 0;

    for (a = 0; a < NANG; a = a + 1) begin
      set_angle(a);
      best_err = 32'h7fffffff; best_so = -1; locks = 0;
      for (so = 0; so <= 7; so = so + 1) begin
        run_off(so);
        if (rxsyms == SYMS[INDEX_W-1:0]) begin
          locks = locks + 1;
          if (errs < best_err) begin best_err = errs; best_so = so; end
        end
      end
      if (best_so < 0) begin
        $display("FAIL: carrier phase %0d deg -- Costas did not acquire inside the preamble (no lock)", deg);
        failures = failures + 1;
      end else if (best_err != 0) begin
        $display("FAIL: carrier phase %0d deg -- locked but %0d/%0d bit errors (loop still settling)",
                 deg, best_err, EXPECT_BITS);
        failures = failures + 1;
      end else begin
        $display("  carrier phase %0d deg: acquired, lock %0d/8 phases, BER 0/%0d", deg, locks, EXPECT_BITS);
      end
    end

    if (failures == 0)
      $display("PASS: qpsk_costas_acquire -- loop pulls in every carrier phase within the 12-symbol preamble");
    else
      $display("FAIL: qpsk_costas_acquire -- %0d carrier phase(s) failed", failures);
    $finish;
  end
endmodule
