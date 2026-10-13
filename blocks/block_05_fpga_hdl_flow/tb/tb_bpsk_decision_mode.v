// Lab 5.10 - rx_decision_mode = 01 (inverted I decisions) on a straight loopback.
//
// Found on silicon (board B, PL fabric loopback, 2026-10-14): with decision mode 01 the BPSK frame
// never locked at any start offset, while mode 00 decoded at BER 0. The matched filter saturates
// at -32768 and the decision mux computed -sym_i, which overflows back to -32768, so saturated
// "1" symbols were not inverted and the stream was corrupted. The fix inverts with ~sym_i.
//
// This bench loops TX straight into RX (no sign flip) and runs two frames back to back:
//   frame 1, decision mode 00: lock_inverted = 0, zero errors;
//   frame 2, decision mode 01: lock_inverted = 1, zero errors.
// It also checks that the decision sample really reached -32768 during the run, so the bench
// keeps covering the overflow case it was written for.

`timescale 1ns/1ps

module tb_bpsk_decision_mode;

localparam integer W = 16;
localparam integer INDEX_W = 16;
localparam integer FLUSH_SYMBOLS = 16;
localparam integer LOOPBACK_SAMPLE_DELAY = 24;
localparam integer MAX_WAIT_CYCLES = 65536;

reg clk = 1'b0;
reg rst = 1'b1;
reg start = 1'b0;
reg [1:0] decision_mode = 2'b00;
reg [INDEX_W-1:0] frame_bit_count_cfg = '0;
reg [INDEX_W-1:0] preamble_count_cfg = '0;
reg [INDEX_W-1:0] start_offset_cfg = '0;

wire busy, done, tx_valid, lock_inverted, debug_symbol_valid;
wire signed [W-1:0] tx_i, tx_q, debug_symbol_i;
wire [INDEX_W-1:0] received_bits, total_errors, payload_errors;

reg [LOOPBACK_SAMPLE_DELAY-1:0] rx_valid_pipe = {LOOPBACK_SAMPLE_DELAY{1'b0}};
reg signed [W-1:0] rx_i_pipe [0:LOOPBACK_SAMPLE_DELAY-1];
reg signed [W-1:0] rx_q_pipe [0:LOOPBACK_SAMPLE_DELAY-1];
integer k, meta_fd, scan_count, tmp_start_offset, tmp_sps, tmp_expected_bits, tmp_preamble_count;
integer tmp_flush_symbols, wait_cycles, frame, errors = 0;
integer sym_min = 32767;
reg [1023:0] line;

bpsk_zynq_ber_top #(
    .W(W), .SPS(8), .INDEX_W(INDEX_W), .MAX_FRAME_BITS(512), .PHASE_W(3), .FLUSH_SYMBOLS(FLUSH_SYMBOLS)
) dut (
    .clk(clk), .rst(rst), .start(start),
    .frame_bit_count(frame_bit_count_cfg), .preamble_count(preamble_count_cfg), .start_offset(start_offset_cfg),
    .busy(busy), .done(done), .tx_valid(tx_valid), .tx_i(tx_i), .tx_q(tx_q),
    .rx_valid(rx_valid_pipe[LOOPBACK_SAMPLE_DELAY-1]),
    .rx_i(rx_i_pipe[LOOPBACK_SAMPLE_DELAY-1]),          // straight: no sign flip in the loop
    .rx_q(rx_q_pipe[LOOPBACK_SAMPLE_DELAY-1]),
    .rx_decision_mode(decision_mode),
    .timed_out(), .received_bits(received_bits), .total_errors(total_errors), .payload_errors(payload_errors),
    .lock_inverted(lock_inverted),
    .debug_recovered_valid(), .debug_recovered_bit(),
    .debug_symbol_valid(debug_symbol_valid), .debug_symbol_i(debug_symbol_i)
);

always #5 clk = ~clk;

always @(posedge clk) begin
    rx_valid_pipe <= {rx_valid_pipe[LOOPBACK_SAMPLE_DELAY-2:0], tx_valid};
    rx_i_pipe[0] <= tx_i;
    rx_q_pipe[0] <= tx_q;
    for (k = 1; k < LOOPBACK_SAMPLE_DELAY; k = k + 1) begin
        rx_i_pipe[k] <= rx_i_pipe[k - 1];
        rx_q_pipe[k] <= rx_q_pipe[k - 1];
    end
    // Mode 00 frame only: the raw matched-filter output must hit the negative rail.
    if (debug_symbol_valid && decision_mode == 2'b00 && $signed(debug_symbol_i) < sym_min)
        sym_min = $signed(debug_symbol_i);
end

task run_frame(input [1:0] mode, input expect_inverted);
    begin
        decision_mode = mode;
        @(negedge clk); start = 1'b1; @(negedge clk); start = 1'b0;
        for (wait_cycles = 0; wait_cycles < MAX_WAIT_CYCLES && !done; wait_cycles = wait_cycles + 1)
            @(posedge clk);
        repeat (3) @(posedge clk);
        if (wait_cycles >= MAX_WAIT_CYCLES || received_bits != frame_bit_count_cfg || total_errors != 0 ||
            payload_errors != 0 || lock_inverted !== expect_inverted) begin
            $display("FAIL decision mode %0d: received %0d/%0d, total errors %0d, payload errors %0d, lock_inverted %0b (expected %0b)",
                     mode, received_bits, frame_bit_count_cfg, total_errors, payload_errors, lock_inverted, expect_inverted);
            errors = errors + 1;
        end else begin
            $display("  decision mode %0d: %0d bits, 0 errors, lock_inverted=%0b", mode, received_bits, lock_inverted);
        end
        while (busy) @(posedge clk);
        repeat (40) @(posedge clk);
    end
endtask

initial begin
    for (k = 0; k < LOOPBACK_SAMPLE_DELAY; k = k + 1) begin
        rx_i_pipe[k] = 0;
        rx_q_pipe[k] = 0;
    end
    meta_fd = $fopen("blocks/block_05_fpga_hdl_flow/tb/bpsk_framed_loopback_meta.txt", "r");
    if (meta_fd == 0) begin
        $display("FAIL cannot open metadata file");
        $fatal(1);
    end
    scan_count = $fgets(line, meta_fd);
    scan_count = $fscanf(meta_fd, "%d %d %d %d %d\n", tmp_start_offset, tmp_sps, tmp_expected_bits,
                         tmp_preamble_count, tmp_flush_symbols);
    $fclose(meta_fd);
    start_offset_cfg = tmp_start_offset[INDEX_W-1:0];
    frame_bit_count_cfg = tmp_expected_bits[INDEX_W-1:0];
    preamble_count_cfg = tmp_preamble_count[INDEX_W-1:0];

    repeat (3) @(posedge clk);
    @(negedge clk); rst = 1'b0;
    run_frame(2'b00, 1'b0);
    run_frame(2'b01, 1'b1);
    if (sym_min != -32768) begin
        $display("FAIL the matched filter never reached -32768 (min %0d): this bench no longer covers the overflow case",
                 sym_min);
        errors = errors + 1;
    end
    if (errors == 0) begin
        $display("PASS: tb_bpsk_decision_mode - inverted decisions lock inverted at BER 0 with the filter on the -32768 rail");
        $finish;
    end else begin
        $display("FAIL: tb_bpsk_decision_mode errors=%0d", errors);
        $fatal(1);
    end
end

endmodule
