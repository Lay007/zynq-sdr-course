// Lab 5.12b - the QPSK Costas quadrant ambiguity, and the frame-sync that resolves it.
//
// A Costas loop has four stable lock points, so after carrier recovery the constellation
// is axis-aligned but rotated by an arbitrary k*90 degrees. This testbench drives the REAL
// self-OTA capture through the full RX chain four times, rotating the input by 0/90/180/270
// degrees, and checks that the frame locks and decodes to BER=0 every time.
//
// Rotation commutes with the DC blocker and the matched filter (both are per-axis with real
// coefficients), so rotating the raw samples rotates the recovered symbols identically.
//
// Before the dual-branch frame-sync in qpsk_ber_counter, 90 and 270 degrees never locked --
// on hardware that lost about half of all bursts.

`timescale 1ns/1ps

module tb_qpsk_quadrant_resolve;
  localparam W = 16, INDEX_W = 16, SYMS = 140, CHAIN_SYMS = 450, NS = 4000;
  localparam integer EXPECT_BITS = 2 * SYMS;

  reg clk = 0, rst = 1, rx_valid = 0, cnt_start = 0;
  reg signed [W-1:0] rx_i = 0, rx_q = 0;
  reg signed [W-1:0] raw_i, raw_q;
  reg [INDEX_W-1:0] start_offset = 0;
  reg [31:0] samp [0:NS-1];
  reg [1:0] rot;
  integer n, so, w, r;
  integer best_err, best_so, failures;
  reg [INDEX_W-1:0] rxsyms, errs;

  wire rxdv;
  wire [1:0] rxdibit;

  qpsk_rx_bit_recovery_chain #(.W(W), .SPS(8), .INDEX_W(INDEX_W)) rxc (
      .clk(clk), .rst(rst), .rst_carrier(rst), .dc_block_en(1'b1), .costas_en(1'b1),
      .coarse_cfo_en(1'b0), .phase_pick_en(1'b0),
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

  task run_off(input integer offs);
    begin
      start_offset = offs[INDEX_W-1:0];
      rst = 1; rx_valid = 0; cnt_start = 0;
      @(negedge clk); @(negedge clk); rst = 0; @(negedge clk);
      cnt_start = 1; @(negedge clk); cnt_start = 0;
      for (n = 0; n < NS; n = n + 1) begin
        raw_i = samp[n][31:16];
        raw_q = samp[n][15:0];
        case (rot)
          2'd0: begin rx_i =  raw_i; rx_q =  raw_q; end   //   0 deg
          2'd1: begin rx_i = -raw_q; rx_q =  raw_i; end   //  90 deg
          2'd2: begin rx_i = -raw_i; rx_q = -raw_q; end   // 180 deg
          default: begin rx_i = raw_q; rx_q = -raw_i; end // 270 deg
        endcase
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

    for (r = 0; r < 4; r = r + 1) begin
      rot = r[1:0];
      best_err = 32'h7fffffff; best_so = -1;
      for (so = 0; so <= 15; so = so + 1) begin
        run_off(so);
        if (rxsyms == SYMS[INDEX_W-1:0] && errs < best_err) begin
          best_err = errs;
          best_so = so;
        end
      end
      if (best_so < 0) begin
        $display("FAIL: rotation %0d deg -- no frame lock at any sampler phase", r * 90);
        failures = failures + 1;
      end else if (best_err != 0) begin
        $display("FAIL: rotation %0d deg -- best %0d/%0d bit errors (offset %0d)",
                 r * 90, best_err, EXPECT_BITS, best_so);
        failures = failures + 1;
      end else begin
        $display("  rotation %0d deg: locked, %0d/%0d bit errors (offset %0d, branch %0s)",
                 r * 90, best_err, EXPECT_BITS, best_so, cswap ? "B(90/270)" : "A(0/180)");
      end
    end

    if (failures == 0)
      $display("PASS: qpsk_quadrant_resolve -- all four Costas lock quadrants decode (BER 0/%0d)", EXPECT_BITS);
    else
      $display("FAIL: qpsk_quadrant_resolve -- %0d rotation(s) failed", failures);
    $finish;
  end
endmodule
