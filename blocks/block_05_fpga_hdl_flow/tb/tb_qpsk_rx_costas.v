`timescale 1ns/1ps
// Defaults track the shipped COSTAS_KP_LOG/KI_LOG; override with -P to re-sweep the gains.
module tb_qpsk_rx_costas #(parameter integer KP=8, parameter integer KI=1);
  localparam W=16, INDEX_W=16, SYMS=140, CHAIN_SYMS=450, NS=4000;
  reg clk=0, rst=1, rx_valid=0, cnt_start=0, dc_en=1, cos_en=1;
  reg signed [W-1:0] rx_i=0, rx_q=0;
  reg [INDEX_W-1:0] start_offset=0;
  reg [31:0] samp [0:NS-1];
  integer n, so, w, cpass;
  integer best_err, best_so;
  reg [INDEX_W-1:0] rxsyms, errs;
  wire rxdv; wire [1:0] rxdibit;
  qpsk_rx_bit_recovery_chain #(.W(W),.SPS(8),.INDEX_W(INDEX_W),.COSTAS_KP_LOG_ACQ(KP),.COSTAS_KP_LOG_TRACK(KP),.COSTAS_KI_LOG(KI)) rxc (
    .clk(clk),.rst(rst),.rst_carrier(rst), .dc_block_en(dc_en),.costas_en(cos_en),
    .coarse_cfo_en(1'b0), .phase_pick_en(1'b0),
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
      rx_valid=0; w=0; while(!cdone && w<4096) begin @(posedge clk); w=w+1; end @(posedge clk);
      rxsyms=rsym; errs=terr;
    end
  endtask
  initial begin
    $readmemh("blocks/block_05_fpga_hdl_flow/tb/qpsk_selfota_fresh_rx.mem", samp);
    repeat(4) @(negedge clk);
    cos_en=1; best_err=32'h7fffffff; best_so=-1;
    for (so=0; so<=15; so=so+1) begin run_off(so); if (rxsyms==SYMS[INDEX_W-1:0] && errs<best_err) begin best_err=errs; best_so=so; end end
    $display("KP=%0d KI=%0d Costas ON: best off=%0d bit_errors=%0d/280", KP, KI, best_so, best_err);
    if (best_so < 0) begin
      $display("FAIL: qpsk_rx_costas -- no frame lock on the real self-OTA capture");
      $fatal(1);
    end else if (best_err != 0) begin
      $display("FAIL: qpsk_rx_costas -- %0d/280 bit errors on the real self-OTA capture", best_err);
      $fatal(1);
    end
    $display("PASS: qpsk_rx_costas -- real self-OTA capture decodes at BER 0/280");
    $finish;
  end
endmodule
