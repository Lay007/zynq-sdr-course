// Lab 5.9 - self-checking framed BPSK TX/RX loopback
//
// Flow:
// framed source bits -> TX chain with auto-flush -> matched filter ->
// fixed-phase symbol timing -> hard decision -> compare against source bits.

`timescale 1ns/1ps

module tb_bpsk_framed_loopback;

localparam integer W = 16;
localparam integer INDEX_W = 16;
localparam integer FLUSH_SYMBOLS = 16;
localparam integer MAX_BITS = 512;
localparam integer CLK_PERIOD_NS = 10;
localparam integer MAX_WAIT_CYCLES = 65536;

reg clk = 1'b0;
reg rst = 1'b1;
reg src_valid = 1'b0;
reg src_bit = 1'b0;
reg src_last = 1'b0;
reg [INDEX_W-1:0] start_offset_cfg = '0;
reg [INDEX_W-1:0] symbol_count_cfg = '0;

wire src_ready;
wire tx_valid;
wire signed [W-1:0] tx_i;
wire signed [W-1:0] tx_q;
wire rx_valid;
wire rx_bit;

reg input_valid_mem [0:MAX_BITS-1];
reg input_bit_mem [0:MAX_BITS-1];
reg input_last_mem [0:MAX_BITS-1];
reg expected_valid_mem [0:MAX_BITS-1];
reg expected_bit_mem [0:MAX_BITS-1];

integer input_count = 0;
integer expected_bit_count = 0;
integer preamble_count = 0;
integer recovered_count = 0;
integer total_errors = 0;
integer payload_errors = 0;

integer idx;
integer wait_cycles;
integer input_fd;
integer expected_fd;
integer meta_fd;
integer scan_count;
integer tmp_valid;
integer tmp_bit;
integer tmp_last;
integer tmp_start_offset;
integer tmp_sps;
integer tmp_expected_bits;
integer tmp_preamble_count;
integer tmp_flush_symbols;
reg [1023:0] line;

bpsk_framed_tx_chain #(
    .W(W),
    .SPS(8),
    .PHASE_W(3),
    .FLUSH_SYMBOLS(FLUSH_SYMBOLS),
    .COUNT_W(INDEX_W)
) tx_chain_i (
    .clk(clk),
    .rst(rst),
    .s_valid(src_valid),
    .s_bit(src_bit),
    .s_last(src_last),
    .s_ready(src_ready),
    .m_valid(tx_valid),
    .m_i(tx_i),
    .m_q(tx_q),
    .busy()
);

bpsk_rx_bit_recovery_chain #(
    .W(W),
    .SPS(8),
    .INDEX_W(INDEX_W)
) rx_chain_i (
    .clk(clk),
    .rst(rst),
    .in_valid(tx_valid),
    .in_i(tx_i),
    .in_q(tx_q),
    .start_offset(start_offset_cfg),
    .symbol_count(symbol_count_cfg),
    .out_valid(rx_valid),
    .out_bit(rx_bit)
);

always #(CLK_PERIOD_NS/2) clk = ~clk;

task read_vectors;
    input [1023:0] input_path;
    input [1023:0] expected_path;
    input [1023:0] meta_path;
    begin
        input_fd = $fopen(input_path, "r");
        if (input_fd == 0) begin
            $display("ERROR: cannot open input bit file");
            $fatal(1);
        end

        expected_fd = $fopen(expected_path, "r");
        if (expected_fd == 0) begin
            $display("ERROR: cannot open expected bit file");
            $fatal(1);
        end

        meta_fd = $fopen(meta_path, "r");
        if (meta_fd == 0) begin
            $display("ERROR: cannot open metadata file");
            $fatal(1);
        end

        scan_count = $fgets(line, input_fd);
        scan_count = $fgets(line, expected_fd);
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
        symbol_count_cfg = tmp_expected_bits[INDEX_W-1:0];
        preamble_count = tmp_preamble_count;

        input_count = 0;
        while (!$feof(input_fd)) begin
            scan_count = $fscanf(input_fd, "%d %d %d\n", tmp_valid, tmp_bit, tmp_last);
            if (scan_count == 3) begin
                if (input_count >= MAX_BITS) begin
                    $display("ERROR: increase MAX_BITS");
                    $fatal(1);
                end
                input_valid_mem[input_count] = tmp_valid[0];
                input_bit_mem[input_count] = tmp_bit[0];
                input_last_mem[input_count] = tmp_last[0];
                input_count = input_count + 1;
            end else if (scan_count != -1) begin
                $display("ERROR: failed to parse input row %0d", input_count);
                $fatal(1);
            end
        end

        expected_bit_count = 0;
        while (!$feof(expected_fd)) begin
            scan_count = $fscanf(expected_fd, "%d %d\n", tmp_valid, tmp_bit);
            if (scan_count == 2) begin
                if (expected_bit_count >= MAX_BITS) begin
                    $display("ERROR: increase MAX_BITS");
                    $fatal(1);
                end
                expected_valid_mem[expected_bit_count] = tmp_valid[0];
                expected_bit_mem[expected_bit_count] = tmp_bit[0];
                expected_bit_count = expected_bit_count + 1;
            end else if (scan_count != -1) begin
                $display("ERROR: failed to parse expected row %0d", expected_bit_count);
                $fatal(1);
            end
        end

        if (input_count != expected_bit_count || expected_bit_count != tmp_expected_bits) begin
            $display(
                "ERROR: input/expected/meta count mismatch (%0d / %0d / %0d)",
                input_count,
                expected_bit_count,
                tmp_expected_bits
            );
            $fatal(1);
        end

        $fclose(input_fd);
        $fclose(expected_fd);
        $fclose(meta_fd);
    end
endtask

initial begin
    read_vectors(
        "blocks/block_05_fpga_hdl_flow/tb/bpsk_framed_loopback_input_bits.txt",
        "blocks/block_05_fpga_hdl_flow/tb/bpsk_framed_loopback_expected_bits.txt",
        "blocks/block_05_fpga_hdl_flow/tb/bpsk_framed_loopback_meta.txt"
    );

    $dumpfile("blocks/block_05_fpga_hdl_flow/tb/tb_bpsk_framed_loopback.vcd");
    $dumpvars(0, tb_bpsk_framed_loopback);

    repeat (3) @(posedge clk);
    @(negedge clk);
    rst = 1'b0;

    idx = 0;
    while (idx < input_count) begin
        @(negedge clk);
        if (src_ready) begin
            src_valid = input_valid_mem[idx];
            src_bit = input_bit_mem[idx];
            src_last = input_last_mem[idx];
            idx = idx + 1;
        end else begin
            src_valid = 1'b0;
            src_bit = 1'b0;
            src_last = 1'b0;
        end
    end

    @(negedge clk);
    src_valid = 1'b0;
    src_bit = 1'b0;
    src_last = 1'b0;

    for (wait_cycles = 0; wait_cycles < MAX_WAIT_CYCLES && recovered_count < expected_bit_count; wait_cycles = wait_cycles + 1) begin
        @(posedge clk);
    end

    if (recovered_count != expected_bit_count) begin
        $display("ERROR: recovered %0d bits, expected %0d", recovered_count, expected_bit_count);
        $fatal(1);
    end

    repeat (3) @(posedge clk);

    if (total_errors == 0) begin
        $display(
            "PASS: bpsk_framed_loopback completed without errors (%0d bits, payload errors %0d)",
            expected_bit_count,
            payload_errors
        );
        $finish;
    end else begin
        $display(
            "FAIL: bpsk_framed_loopback completed with total/payload errors = %0d / %0d",
            total_errors,
            payload_errors
        );
        $fatal(1);
    end
end

always @(posedge clk) begin
    if (!rst && rx_valid) begin
        if (recovered_count >= expected_bit_count) begin
            $display("ERROR at %0t: unexpected extra recovered bit %0b", $time, rx_bit);
            total_errors = total_errors + 1;
        end else begin
            if (!expected_valid_mem[recovered_count]) begin
                $display("ERROR at %0t: expected bit %0d is marked invalid", $time, recovered_count);
                total_errors = total_errors + 1;
            end else if (rx_bit !== expected_bit_mem[recovered_count]) begin
                $display(
                    "ERROR at %0t: recovered bit=%0b expected=%0b index=%0d",
                    $time,
                    rx_bit,
                    expected_bit_mem[recovered_count],
                    recovered_count
                );
                total_errors = total_errors + 1;
                if (recovered_count >= preamble_count) begin
                    payload_errors = payload_errors + 1;
                end
            end
            recovered_count = recovered_count + 1;
        end
    end
end

endmodule
