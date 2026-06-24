// Lab 5.10 - self-checking deterministic Zynq-ready BPSK BER top-level
//
// The testbench delays and sign-inverts the TX sample stream before looping it
// back into RX, then verifies the integrated start/busy/done and BER contract.

`timescale 1ns/1ps

module tb_bpsk_zynq_ber_top;

localparam integer W = 16;
localparam integer INDEX_W = 16;
localparam integer FLUSH_SYMBOLS = 16;
localparam integer LOOPBACK_SAMPLE_DELAY = 24;
localparam integer MAX_WAIT_CYCLES = 65536;
localparam integer CLK_PERIOD_NS = 10;

reg clk = 1'b0;
reg rst = 1'b1;
reg start = 1'b0;
reg [INDEX_W-1:0] frame_bit_count_cfg = '0;
reg [INDEX_W-1:0] preamble_count_cfg = '0;
reg [INDEX_W-1:0] start_offset_cfg = '0;

wire busy;
wire done;
wire tx_valid;
wire signed [W-1:0] tx_i;
wire signed [W-1:0] tx_q;
wire delayed_rx_valid;
wire signed [W-1:0] delayed_rx_i;
wire signed [W-1:0] delayed_rx_q;
wire [INDEX_W-1:0] received_bits;
wire [INDEX_W-1:0] total_errors;
wire [INDEX_W-1:0] payload_errors;

integer wait_cycles;
integer meta_fd;
integer scan_count;
integer tmp_start_offset;
integer tmp_sps;
integer tmp_expected_bits;
integer tmp_preamble_count;
integer tmp_flush_symbols;
integer delay_idx;
reg [1023:0] line;
reg saw_busy = 1'b0;
reg saw_tx_valid = 1'b0;
reg saw_done = 1'b0;
reg [LOOPBACK_SAMPLE_DELAY-1:0] rx_valid_pipe = {LOOPBACK_SAMPLE_DELAY{1'b0}};
reg signed [W-1:0] rx_i_pipe [0:LOOPBACK_SAMPLE_DELAY-1];
reg signed [W-1:0] rx_q_pipe [0:LOOPBACK_SAMPLE_DELAY-1];

bpsk_zynq_ber_top #(
    .W(W),
    .SPS(8),
    .INDEX_W(INDEX_W),
    .MAX_FRAME_BITS(512),
    .PHASE_W(3),
    .FLUSH_SYMBOLS(FLUSH_SYMBOLS)
) dut (
    .clk(clk),
    .rst(rst),
    .start(start),
    .frame_bit_count(frame_bit_count_cfg),
    .preamble_count(preamble_count_cfg),
    .start_offset(start_offset_cfg),
    .busy(busy),
    .done(done),
    .tx_valid(tx_valid),
    .tx_i(tx_i),
    .tx_q(tx_q),
    .rx_valid(delayed_rx_valid),
    .rx_i(-delayed_rx_i),
    .rx_q(delayed_rx_q),
    .rx_decision_mode(2'b00),
    .timed_out(),
    .received_bits(received_bits),
    .total_errors(total_errors),
    .payload_errors(payload_errors),
    .debug_recovered_valid(),
    .debug_recovered_bit(),
    .debug_symbol_valid(),
    .debug_symbol_i()
);

always #(CLK_PERIOD_NS/2) clk = ~clk;

assign delayed_rx_valid = rx_valid_pipe[LOOPBACK_SAMPLE_DELAY-1];
assign delayed_rx_i = rx_i_pipe[LOOPBACK_SAMPLE_DELAY-1];
assign delayed_rx_q = rx_q_pipe[LOOPBACK_SAMPLE_DELAY-1];

task read_meta;
    input [1023:0] meta_path;
    begin
        meta_fd = $fopen(meta_path, "r");
        if (meta_fd == 0) begin
            $display("ERROR: cannot open metadata file");
            $fatal(1);
        end

        scan_count = $fgets(line, meta_fd);
        scan_count = $fscanf(meta_fd, "%d %d %d %d %d\n", tmp_start_offset, tmp_sps, tmp_expected_bits, tmp_preamble_count, tmp_flush_symbols);
        if (scan_count != 5) begin
            $display("ERROR: failed to parse metadata");
            $fatal(1);
        end
        if (tmp_sps != 8) begin
            $display("ERROR: expected SPS=8, got %0d", tmp_sps);
            $fatal(1);
        end
        if (tmp_flush_symbols != FLUSH_SYMBOLS) begin
            $display("ERROR: expected FLUSH_SYMBOLS=%0d, got %0d", FLUSH_SYMBOLS, tmp_flush_symbols);
            $fatal(1);
        end

        start_offset_cfg = tmp_start_offset[INDEX_W-1:0];
        frame_bit_count_cfg = tmp_expected_bits[INDEX_W-1:0];
        preamble_count_cfg = tmp_preamble_count[INDEX_W-1:0];

        $fclose(meta_fd);
    end
endtask

always @(posedge clk) begin
    if (rst) begin
        rx_valid_pipe <= {LOOPBACK_SAMPLE_DELAY{1'b0}};
        for (delay_idx = 0; delay_idx < LOOPBACK_SAMPLE_DELAY; delay_idx = delay_idx + 1) begin
            rx_i_pipe[delay_idx] <= {W{1'b0}};
            rx_q_pipe[delay_idx] <= {W{1'b0}};
        end
    end else begin
        rx_valid_pipe[0] <= tx_valid;
        rx_i_pipe[0] <= tx_i;
        rx_q_pipe[0] <= tx_q;
        for (delay_idx = 1; delay_idx < LOOPBACK_SAMPLE_DELAY; delay_idx = delay_idx + 1) begin
            rx_valid_pipe[delay_idx] <= rx_valid_pipe[delay_idx - 1];
            rx_i_pipe[delay_idx] <= rx_i_pipe[delay_idx - 1];
            rx_q_pipe[delay_idx] <= rx_q_pipe[delay_idx - 1];
        end
    end
end

initial begin
    read_meta("blocks/block_05_fpga_hdl_flow/tb/bpsk_framed_loopback_meta.txt");

    $dumpfile("blocks/block_05_fpga_hdl_flow/tb/tb_bpsk_zynq_ber_top.vcd");
    $dumpvars(0, tb_bpsk_zynq_ber_top);

    repeat (3) @(posedge clk);
    @(negedge clk);
    rst = 1'b0;

    @(negedge clk);
    start = 1'b1;
    @(negedge clk);
    start = 1'b0;

    for (wait_cycles = 0; wait_cycles < MAX_WAIT_CYCLES && !saw_done; wait_cycles = wait_cycles + 1) begin
        @(posedge clk);
    end

    if (!saw_busy) begin
        $display("ERROR: top-level busy was never asserted");
        $fatal(1);
    end
    if (!saw_tx_valid) begin
        $display("ERROR: top-level never emitted TX samples");
        $fatal(1);
    end
    if (!saw_done) begin
        $display("ERROR: top-level done was never asserted");
        $fatal(1);
    end
    if (busy) begin
        $display("ERROR: top-level busy remained asserted after completion");
        $fatal(1);
    end
    if (received_bits != frame_bit_count_cfg) begin
        $display("ERROR: received_bits=%0d expected=%0d", received_bits, frame_bit_count_cfg);
        $fatal(1);
    end
    if (total_errors != 0 || payload_errors != 0) begin
        $display(
            "ERROR: total_errors=%0d payload_errors=%0d",
            total_errors,
            payload_errors
        );
        $fatal(1);
    end

    repeat (3) @(posedge clk);
    $display(
        "PASS: bpsk_zynq_ber_top completed without errors (%0d bits, payload errors %0d)",
        received_bits,
        payload_errors
    );
    $finish;
end

always @(posedge clk) begin
    if (!rst) begin
        if (busy) begin
            saw_busy <= 1'b1;
        end
        if (tx_valid) begin
            saw_tx_valid <= 1'b1;
        end
        if (done) begin
            saw_done <= 1'b1;
        end
    end
end

endmodule
