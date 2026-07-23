// Lab 5.14b - coarse CFO through the REAL matched-filter chain.
//
// tb_qpsk_coarse_cfo proves the estimator on clean symbols. This proves it in place, after the
// matched filter, which sees the CFO rotating ~22 deg across each RRC pulse:
//   dc_blocker -> bpsk_rrc_rx_fir (MF) -> sampler -> qpsk_coarse_cfo -> costas -> decision -> counter
// on pulse-shaped, hardware-amplitude bursts (symbol centres ~+-2000 after the RX MF, the level
// the RX gain lands on real self-OTA -- and the coarse CFO's design point; the y4 datapath
// tolerates |sym| up to ~16000, which proper RX gain keeps well under).
//
// Sweeps start_offset (MF group delay + sampling phase) and asserts: a 25 kHz offset that the
// Costas cannot pull in is removed by the estimator and the frame decodes at BER 0; the same
// offset breaks the frame with the estimator bypassed; a near-zero offset is left alone.

`timescale 1ns/1ps

module tb_qpsk_coarse_cfo_chain;
  localparam W=16, INDEX_W=16, SYMS=140, NS=4096, FEED=2200;
  localparam integer EXPECT_BITS = 2*SYMS;

  reg clk=0, rst=1, vld=0, cnt_start=0, cfo_en=1;
  reg signed [W-1:0] ii=0, qq=0;
  reg [INDEX_W-1:0] soff=0;
  reg [31:0] samp [0:NS-1];
  integer n, w, so, best_err, best_so, locks, failures;

  wire dcv; wire signed [W-1:0] dci,dcq;
  dc_blocker #(.W(W),.K_MAX(10)) dcb (.clk(clk),.rst(rst),.enable(1'b0),
    .in_valid(vld),.in_i(ii),.in_q(qq),.out_valid(dcv),.out_i(dci),.out_q(dcq));
  wire mfv; wire signed [W-1:0] mfi,mfq;
  bpsk_rrc_rx_fir mf (.clk(clk),.rst(rst),.in_valid(dcv),.in_i(dci),.in_q(dcq),
    .out_valid(mfv),.out_i(mfi),.out_q(mfq));
  wire sv; wire signed [W-1:0] si,sq;
  bpsk_symbol_timing_sampler #(.W(W),.SPS(8),.INDEX_W(INDEX_W)) smp (
    .clk(clk),.rst(rst),.in_valid(mfv),.in_i(mfi),.in_q(mfq),
    .start_offset(soff),.symbol_count(16'd260),.out_valid(sv),.out_i(si),.out_q(sq));
  wire cvo,crdy; wire signed [W-1:0] ci,cq; wire signed [23:0] omega;
  qpsk_coarse_cfo #(.W(W),.WIN_SYMBOLS(64),.SQ_SHIFT(11),.SIG_THRESH(1000)) cfo (
    .clk(clk),.rst(rst),.enable(cfo_en),.in_valid(sv),.in_i(si),.in_q(sq),
    .out_valid(cvo),.out_i(ci),.out_q(cq),.cfo_ready(crdy),.cfo_omega(omega));
  wire svo; wire signed [W-1:0] xi,xq;
  qpsk_costas #(.W(W)) cos_i (.clk(clk),.rst(rst),.rst_phase(rst),.enable(1'b1),
    .in_valid(cvo),.in_i(ci),.in_q(cq),.out_valid(svo),.out_i(xi),.out_q(xq));
  wire dvo; wire [1:0] dib;
  qpsk_hard_decision dec (.clk(clk),.rst(rst),.in_valid(svo),.in_i(xi),.in_q(xq),
    .out_valid(dvo),.out_dibit(dib));
  wire cbusy,cdone,cswap; wire [INDEX_W-1:0] rsym,terr;
  qpsk_ber_counter #(.INDEX_W(INDEX_W),.MAX_FRAME_BITS(512),.LOCK_PREAMBLE_BITS(24),.LOCK_ERR_TOL(3)) cnt (
    .clk(clk),.rst(rst),.start(cnt_start),.abort(1'b0),
    .symbol_count(SYMS[INDEX_W-1:0]),.preamble_count(16'd24),
    .in_valid(dvo),.in_dibit(dib),.busy(cbusy),.done(cdone),.quadrant_swapped(cswap),
    .received_symbols(rsym),.total_bit_errors(terr));
  always #5 clk=~clk;

  reg [INDEX_W-1:0] rsym_l, terr_l;
  task run_off(input integer offs);
    begin
      soff=offs[INDEX_W-1:0];
      rst=1; vld=0; cnt_start=0; repeat(4) @(negedge clk); rst=0; @(negedge clk);
      cnt_start=1; @(negedge clk); cnt_start=0;
      for (n=0;n<FEED;n=n+1) begin ii=samp[n][31:16]; qq=samp[n][15:0]; vld=1; @(negedge clk); if (cdone) n=FEED; end
      vld=0; w=0; while(!cdone && w<8192) begin @(posedge clk); w=w+1; end @(posedge clk);
      rsym_l=rsym; terr_l=terr;
    end
  endtask

  // returns best_err (2^31-1 if never locked) and sets best_so/locks
  task sweep(input en);
    begin
      cfo_en=en; best_err=32'h7fffffff; best_so=-1; locks=0;
      for (so=0; so<16; so=so+1) begin
        run_off(so);
        if (rsym_l==SYMS[INDEX_W-1:0]) begin locks=locks+1; if (terr_l<best_err) begin best_err=terr_l; best_so=so; end end
      end
    end
  endtask

  initial begin
    failures=0;

    $readmemh("blocks/block_05_fpga_hdl_flow/tb/srate_cfo25k_rx.mem", samp);
    sweep(1'b0);
    $display("  CFO 25kHz, estimator OFF: lock %0d/16 best_err %0d", locks, (best_so<0)?-1:best_err);
    if (best_so>=0 && best_err<=40) begin $display("FAIL: 25 kHz decoded without correction"); failures=failures+1; end

    sweep(1'b1);
    $display("  CFO 25kHz, estimator ON:  lock %0d/16 best off=%0d err=%0d omega=%0d", locks, best_so, (best_so<0)?-1:best_err, omega);
    if (best_so<0 || best_err!=0) begin $display("FAIL: coarse CFO did not recover the 25 kHz frame through the MF"); failures=failures+1; end

    $readmemh("blocks/block_05_fpga_hdl_flow/tb/srate_cfo0_rx.mem", samp);
    sweep(1'b1);
    $display("  CFO ~0,     estimator ON:  lock %0d/16 best off=%0d err=%0d omega=%0d", locks, best_so, (best_so<0)?-1:best_err, omega);
    if (best_so<0 || best_err!=0) begin $display("FAIL: coarse CFO harmed a zero-offset frame"); failures=failures+1; end

    if (failures==0)
      $display("PASS: qpsk_coarse_cfo_chain -- coarse CFO after the matched filter removes 25 kHz, BER 0/%0d", EXPECT_BITS);
    else
      $display("FAIL: qpsk_coarse_cfo_chain -- %0d check(s) failed", failures);
    $finish;
  end
endmodule
