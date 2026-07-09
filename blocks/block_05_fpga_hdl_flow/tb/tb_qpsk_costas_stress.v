// Freeze-gate validation: reproduce the on-chip burst failure (loop resets per frame,
// then wanders on the leading pre-frame NOISE before the burst arrives) by prepending
// 3000 noise samples to the real capture, and show SIG_THRESH>0 (freeze) recovers it.
`timescale 1ns/1ps
// Default TH matches the shipped COSTAS_SIG_THRESH so the smoke suite exercises the
// configuration that runs on silicon; override with -Ptb_qpsk_costas_stress.TH=0 to see
// the un-gated loop wander on the pre-frame noise.
module tb_qpsk_costas_stress #(parameter integer TH=1000);
  localparam W=16, INDEX_W=16, SYMS=140, CHAIN_SYMS=700, NS=7000;
  reg clk=0, rst=1, rx_valid=0, cnt_start=0;
  reg signed [W-1:0] rx_i=0, rx_q=0;
  reg [INDEX_W-1:0] start_offset=0;
  reg [31:0] samp [0:NS-1];
  integer n, so, w;
  integer best_err, best_so;
  reg [INDEX_W-1:0] rxsyms, errs;
  wire rxdv; wire [1:0] rxdibit;
  qpsk_rx_bit_recovery_chain #(.W(W),.SPS(8),.INDEX_W(INDEX_W),.COSTAS_SIG_THRESH(TH)) rxc (
    .clk(clk),.rst(rst),.dc_block_en(1'b1),.costas_en(1'b1),
    .in_valid(rx_valid),.in_i(rx_i),.in_q(rx_q),
    .start_offset(start_offset),.symbol_count(CHAIN_SYMS[INDEX_W-1:0]),
    .out_valid(rxdv),.out_dibit(rxdibit),
    .debug_symbol_valid(),.debug_symbol_i(),.debug_symbol_q());
  wire cbusy,cdone; wire [INDEX_W-1:0] rsym,terr;
  qpsk_ber_counter #(.INDEX_W(INDEX_W),.MAX_FRAME_BITS(512),.LOCK_PREAMBLE_BITS(24),.LOCK_ERR_TOL(3)) cnt (
    .clk(clk),.rst(rst),.start(cnt_start),.abort(1'b0),
    .symbol_count(SYMS[INDEX_W-1:0]),.preamble_count(16'd24),
    .in_valid(rxdv),.in_dibit(rxdibit),.busy(cbusy),.done(cdone),
    .received_symbols(rsym),.total_bit_errors(terr));
  always #5 clk=~clk;
  task run_off(input integer offs);
    begin
      start_offset=offs[INDEX_W-1:0];
      rst=1; rx_valid=0; cnt_start=0; @(negedge clk); @(negedge clk); rst=0; @(negedge clk);
      cnt_start=1; @(negedge clk); cnt_start=0;
      for (n=0;n<NS;n=n+1) begin rx_i=samp[n][31:16]; rx_q=samp[n][15:0]; rx_valid=1; @(negedge clk); if (cdone) n=NS; end
      rx_valid=0; w=0; while(!cdone && w<8192) begin @(posedge clk); w=w+1; end @(posedge clk);
      rxsyms=rsym; errs=terr;
    end
  endtask
  initial begin
    $readmemh("blocks/block_05_fpga_hdl_flow/tb/qpsk_selfota_stress_rx.mem", samp);
    repeat(4) @(negedge clk);
    best_err=32'h7fffffff; best_so=-1;
    for (so=0; so<=15; so=so+1) begin run_off(so); if (rxsyms==SYMS[INDEX_W-1:0] && errs<best_err) begin best_err=errs; best_so=so; end end
    $display("SIG_THRESH=%0d: best off=%0d recv_ok=%0s bit_errors=%0d/280", TH, best_so, (best_so>=0)?"140":"NONE", best_err);
    if (TH == 0) begin
      $display("NOTE: freeze gate disabled -- result is diagnostic only, not asserted");
    end else if (best_so < 0) begin
      $display("FAIL: qpsk_costas_stress -- no frame lock with the freeze gate on");
      $fatal(1);
    end else if (best_err != 0) begin
      $display("FAIL: qpsk_costas_stress -- %0d/280 bit errors with the freeze gate on", best_err);
      $fatal(1);
    end else begin
      $display("PASS: qpsk_costas_stress -- Costas acquires through 3000 pre-frame noise samples (BER 0/280)");
    end
    $finish;
  end
endmodule
