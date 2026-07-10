// Lab 5.12d - carrier phase across bursts: does holding it help, and when does it stop?
//
// A burst-mode receiver restarts the carrier loop on every frame, so every frame pays the
// pull-in cost. If the RF path phase is quasi-static -- one board hearing its own antenna
// a few centimetres away -- the phase the loop found on burst N is still right on burst
// N+1, and restarting from zero throws that away. `costas_hold_phase` keeps theta/freq
// across frames instead.
//
// The assumption is testable, and this bench tests it rather than trusting it. It replays
// the real self-OTA capture as several back-to-back bursts, ROTATING each burst by an extra
// PHASE_STEP_DEG relative to the previous one:
//
//   PHASE_STEP_DEG = 0   the phase really is static  -> holding should acquire instantly
//   PHASE_STEP_DEG = 40  the phase walks every burst -> holding must not make it worse
//
// Between bursts the sampler window is closed, so the loop sees no symbols at all and the
// held phase simply persists. HOLD=0 reproduces today's behaviour for comparison.

`timescale 1ns/1ps

// KPA/KPT expose the gear shift so the two mechanisms can be told apart. With the shipped
// KPA=8 the loop acquires inside the preamble on its own and HOLD makes no visible
// difference here; drop KPA to 6 (no gear shift) and HOLD is what rescues bursts 2..N.
module tb_qpsk_costas_multiburst #(
    parameter integer HOLD = 1,
    parameter integer PHASE_BASE_DEG = 0,   // carrier phase of the first burst
    parameter integer PHASE_STEP_DEG = 0,
    parameter integer NBURSTS = 4,
    parameter integer KPA = 8,
    parameter integer KPT = 6
);
  localparam W = 16, INDEX_W = 16, SYMS = 140, CHAIN_SYMS = 450, NS = 4000;
  localparam integer EXPECT_BITS = 2 * SYMS;

  reg clk = 0, rst = 1, rx_valid = 0, cnt_start = 0;
  reg signed [W-1:0] rx_i = 0, rx_q = 0;
  reg signed [31:0] raw_i, raw_q, rot_i, rot_q;
  reg signed [31:0] cq, sq;
  reg [INDEX_W-1:0] start_offset = 0;
  reg [31:0] samp [0:NS-1];
  integer n, w, b, deg, clean, locked_cnt;
  reg [INDEX_W-1:0] rxsyms, errs;

  // Per-burst reset: the matched filter and sampler always restart, the carrier loop only
  // when HOLD = 0. This mirrors qpsk_zynq_ber_top's `rst || (frame_start && !hold)`.
  reg frame_rst = 1'b1;
  wire chain_rst   = rst || frame_rst;
  wire carrier_rst = rst || (frame_rst && (HOLD == 0));

  wire rxdv;
  wire [1:0] rxdibit;
  qpsk_rx_bit_recovery_chain #(.W(W), .SPS(8), .INDEX_W(INDEX_W),
                               .COSTAS_KP_LOG_ACQ(KPA), .COSTAS_KP_LOG_TRACK(KPT)) rxc (
      .clk(clk), .rst(chain_rst), .rst_carrier(carrier_rst),
      .dc_block_en(1'b1), .costas_en(1'b1),
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

  // Q15 cos/sin of burst_index * PHASE_STEP_DEG, folded to the four multiples of 10 we need.
  task set_rotation(input integer d);
    begin
      deg = ((d % 360) + 360) % 360;
      case (deg)
         0: begin cq =  32767; sq =      0; end
        40: begin cq =  25101; sq =  21063; end
        80: begin cq =   5690; sq =  32270; end
       120: begin cq = -16384; sq =  28378; end
       160: begin cq = -30792; sq =  11207; end
       200: begin cq = -30792; sq = -11207; end
       240: begin cq = -16384; sq = -28378; end
       280: begin cq =   5690; sq = -32270; end
       320: begin cq =  25101; sq = -21063; end
       default: begin cq = 32767; sq = 0; end
      endcase
    end
  endtask

  // One burst: pulse the per-frame reset, start the counter, stream the (rotated) capture.
  task run_burst(input integer rot_deg);
    begin
      set_rotation(rot_deg);
      frame_rst = 1'b1; rx_valid = 0; cnt_start = 0;
      @(negedge clk); @(negedge clk);
      frame_rst = 1'b0;
      @(negedge clk);
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
      // inter-burst silence: no symbols reach the loop, so a held phase just persists
      repeat (64) @(negedge clk);
    end
  endtask

  initial begin
    $readmemh("blocks/block_05_fpga_hdl_flow/tb/qpsk_selfota_fresh_rx.mem", samp);
    repeat (4) @(negedge clk);
    rst = 0;
    start_offset = 16'd1;      // the sampler phase this capture decodes at
    clean = 0; locked_cnt = 0;

    for (b = 0; b < NBURSTS; b = b + 1) begin
      run_burst(PHASE_BASE_DEG + b * PHASE_STEP_DEG);
      if (rxsyms == SYMS[INDEX_W-1:0]) begin
        locked_cnt = locked_cnt + 1;
        if (errs == 0) clean = clean + 1;
      end
      $display("  burst %0d (phase %0d deg): recv=%0d/%0d errors=%0d/%0d",
               b, deg, rxsyms, SYMS, errs, EXPECT_BITS);
    end

    $display("HOLD=%0d step=%0d deg: lock %0d/%0d, clean %0d/%0d",
             HOLD, PHASE_STEP_DEG, locked_cnt, NBURSTS, clean, NBURSTS);

    // The shipped configuration must decode every burst of a static-phase link.
    if (HOLD == 1 && PHASE_STEP_DEG == 0 && clean != NBURSTS) begin
      $display("FAIL: qpsk_costas_multiburst -- holding the phase lost %0d of %0d static-phase bursts",
               NBURSTS - clean, NBURSTS);
      $fatal(1);
    end
    if (clean != NBURSTS) begin
      $display("FAIL: qpsk_costas_multiburst -- %0d of %0d bursts did not decode", NBURSTS - clean, NBURSTS);
      $fatal(1);
    end
    $display("PASS: qpsk_costas_multiburst -- HOLD=%0d, %0d deg per burst, all %0d bursts BER 0/%0d",
             HOLD, PHASE_STEP_DEG, NBURSTS, EXPECT_BITS);
    $finish;
  end
endmodule
