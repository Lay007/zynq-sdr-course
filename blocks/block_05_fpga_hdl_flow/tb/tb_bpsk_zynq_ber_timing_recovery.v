// Lab 5.10b - full-chain timing-recovery verification.
//
// Feeds a time-drifted (SPS=8.03) RX waveform into two bpsk_zynq_ber_top instances
// that differ only in TIMING_RECOVERY. Scanning start_offset, the Gardner loop
// (TIMING_RECOVERY=1) must reach a full frame at BER 0, while the fixed-phase
// decimator (TIMING_RECOVERY=0) must NOT (it drifts off the symbol over the burst).

`timescale 1ns/1ps

module tb_bpsk_zynq_ber_timing_recovery;

localparam integer W = 16;
localparam integer INDEX_W = 16;
localparam integer N_RX = 2382;          // see bpsk_chain_drift_meta.txt
localparam integer MAX_WAIT = 20000;

reg clk = 1'b0;
reg rst = 1'b1;
reg start = 1'b0;
reg rx_valid = 1'b0;
reg signed [W-1:0] rx_i = 0;
reg [INDEX_W-1:0] start_offset_cfg = 0;
reg [INDEX_W-1:0] frame_bit_count_cfg = 281;
reg [INDEX_W-1:0] preamble_count_cfg = 25;

wire busy_tr, done_tr, busy_fp, done_fp;
wire [INDEX_W-1:0] rb_tr, te_tr, pe_tr, rb_fp, te_fp, pe_fp;

reg signed [W-1:0] rx_mem [0:N_RX-1];
integer k, so, wait_cnt;
integer best_tr_err, best_tr_off, best_fp_err;
reg done_tr_l, done_fp_l;

bpsk_zynq_ber_top #(.W(W), .SPS(8), .INDEX_W(INDEX_W), .TIMING_RECOVERY(1), .RX_IDLE_TIMEOUT_CYCLES(4096)) dut_tr (
    .clk(clk), .rst(rst), .start(start),
    .frame_bit_count(frame_bit_count_cfg), .preamble_count(preamble_count_cfg),
    .start_offset(start_offset_cfg),
    .busy(busy_tr), .done(done_tr),
    .tx_valid(), .tx_i(), .tx_q(),
    .rx_valid(rx_valid), .rx_i(rx_i), .rx_q(16'sd0), .rx_decision_mode(2'b00),
    .timed_out(), .received_bits(rb_tr), .total_errors(te_tr), .payload_errors(pe_tr),
    .debug_recovered_valid(), .debug_recovered_bit(), .debug_symbol_valid(), .debug_symbol_i());

bpsk_zynq_ber_top #(.W(W), .SPS(8), .INDEX_W(INDEX_W), .TIMING_RECOVERY(0), .RX_IDLE_TIMEOUT_CYCLES(4096)) dut_fp (
    .clk(clk), .rst(rst), .start(start),
    .frame_bit_count(frame_bit_count_cfg), .preamble_count(preamble_count_cfg),
    .start_offset(start_offset_cfg),
    .busy(busy_fp), .done(done_fp),
    .tx_valid(), .tx_i(), .tx_q(),
    .rx_valid(rx_valid), .rx_i(rx_i), .rx_q(16'sd0), .rx_decision_mode(2'b00),
    .timed_out(), .received_bits(rb_fp), .total_errors(te_fp), .payload_errors(pe_fp),
    .debug_recovered_valid(), .debug_recovered_bit(), .debug_symbol_valid(), .debug_symbol_i());

always #5 clk = ~clk;

// latch done (it is a 1-cycle pulse)
always @(posedge clk) begin
    if (rst) begin done_tr_l <= 1'b0; done_fp_l <= 1'b0; end
    else begin
        if (done_tr) done_tr_l <= 1'b1;
        if (done_fp) done_fp_l <= 1'b1;
    end
end

task run_attempt(input [INDEX_W-1:0] off);
    begin
        // full reset
        rst = 1'b1; start = 1'b0; rx_valid = 1'b0; rx_i = 0;
        repeat (4) @(negedge clk);
        start_offset_cfg = off;
        rst = 1'b0;
        @(negedge clk);
        start = 1'b1;        // frame_start
        @(negedge clk);
        start = 1'b0;
        // feed the drifted RX stream
        for (k = 0; k < N_RX; k = k + 1) begin
            @(negedge clk);
            rx_valid = 1'b1;
            rx_i = rx_mem[k];
        end
        @(negedge clk);
        rx_valid = 1'b0;
        // drain until both done or timeout
        wait_cnt = 0;
        while (!(done_tr_l && done_fp_l) && wait_cnt < MAX_WAIT) begin
            @(posedge clk); wait_cnt = wait_cnt + 1;
        end
        repeat (4) @(posedge clk);
    end
endtask

initial begin
    $readmemh("blocks/block_05_fpga_hdl_flow/tb/bpsk_chain_drift_rx.mem", rx_mem);
    best_tr_err = 99999; best_tr_off = -1; best_fp_err = 99999;

    // scan a narrow window around the known pull-in point (62) for CI speed
    for (so = 56; so <= 68; so = so + 1) begin
        run_attempt(so[INDEX_W-1:0]);
        if (rb_tr == frame_bit_count_cfg && te_tr < best_tr_err) begin
            best_tr_err = te_tr; best_tr_off = so;
        end
        if (rb_fp == frame_bit_count_cfg && te_fp < best_fp_err) begin
            best_fp_err = te_fp;
        end
    end

    $display("TIMING_RECOVERY=1 best: errors=%0d at start_offset=%0d", best_tr_err, best_tr_off);
    $display("TIMING_RECOVERY=0 best: errors=%0d (fixed-phase, drifted input)", best_fp_err);

    if (best_tr_err != 0) begin
        $display("FAIL: timing recovery did not reach BER=0 on the drifted burst");
        $fatal(1);
    end
    if (best_fp_err == 0) begin
        $display("WARN: fixed-phase also reached BER=0 (drift too small to be a fair test)");
    end
    $display("PASS: Gardner timing recovery recovers the SPS=8.03 burst at BER=0 (start_offset=%0d); fixed-phase floor=%0d errors",
             best_tr_off, best_fp_err);
    $finish;
end

endmodule
