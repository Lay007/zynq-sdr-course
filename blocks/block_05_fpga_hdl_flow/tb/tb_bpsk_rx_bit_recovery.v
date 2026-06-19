// Lab 5.8 - self-checking BPSK RX bit-recovery testbench
//
// Flow:
// corrected capture -> RRC matched filter -> fixed-phase symbol sampler
// -> hard decision -> compare against deterministic Block 11 tx_bits.txt

`timescale 1ns/1ps

module tb_bpsk_rx_bit_recovery;

localparam integer W = 16;
localparam integer INDEX_W = 16;
localparam integer MAX_SAMPLES = 4096;
localparam integer MAX_BITS = 512;
localparam integer CLK_PERIOD_NS = 10;
localparam integer MAX_WAIT_CYCLES = 4096;

reg clk = 1'b0;
reg rst = 1'b1;
reg in_valid = 1'b0;
reg signed [W-1:0] in_i = '0;
reg signed [W-1:0] in_q = '0;
reg [INDEX_W-1:0] start_offset_cfg = '0;
reg [INDEX_W-1:0] symbol_count_cfg = '0;

wire mf_valid;
wire signed [W-1:0] mf_i;
wire signed [W-1:0] mf_q;
wire sym_valid;
wire signed [W-1:0] sym_i;
wire signed [W-1:0] sym_q;
wire bit_valid;
wire bit_out;

reg input_valid_mem [0:MAX_SAMPLES-1];
reg signed [W-1:0] input_i_mem [0:MAX_SAMPLES-1];
reg signed [W-1:0] input_q_mem [0:MAX_SAMPLES-1];
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
integer tmp_i;
integer tmp_q;
integer tmp_bit;
integer tmp_start_offset;
integer tmp_sps;
integer tmp_expected_bits;
integer tmp_preamble_count;
reg [1023:0] line;

bpsk_rrc_rx_fir matched_filter_i (
    .clk(clk),
    .rst(rst),
    .in_valid(in_valid),
    .in_i(in_i),
    .in_q(in_q),
    .out_valid(mf_valid),
    .out_i(mf_i),
    .out_q(mf_q)
);

bpsk_symbol_timing_sampler #(
    .W(W),
    .SPS(8),
    .INDEX_W(INDEX_W)
) timing_sampler_i (
    .clk(clk),
    .rst(rst),
    .in_valid(mf_valid),
    .in_i(mf_i),
    .in_q(mf_q),
    .start_offset(start_offset_cfg),
    .symbol_count(symbol_count_cfg),
    .out_valid(sym_valid),
    .out_i(sym_i),
    .out_q(sym_q)
);

bpsk_hard_decision decision_i (
    .clk(clk),
    .rst(rst),
    .in_valid(sym_valid),
    .in_i(sym_i),
    .out_valid(bit_valid),
    .out_bit(bit_out)
);

always #(CLK_PERIOD_NS/2) clk = ~clk;

task read_vectors;
    input [1023:0] input_path;
    input [1023:0] expected_path;
    input [1023:0] meta_path;
    begin
        input_fd = $fopen(input_path, "r");
        if (input_fd == 0) begin
            $display("ERROR: cannot open input vector file");
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
        scan_count = $fscanf(meta_fd, "%d %d %d %d\n", tmp_start_offset, tmp_sps, tmp_expected_bits, tmp_preamble_count);
        if (scan_count != 4) begin
            $display("ERROR: failed to parse metadata");
            $fatal(1);
        end
        if (tmp_sps != 8) begin
            $display("ERROR: expected SPS=8, got %0d", tmp_sps);
            $fatal(1);
        end
        start_offset_cfg = tmp_start_offset[INDEX_W-1:0];
        symbol_count_cfg = tmp_expected_bits[INDEX_W-1:0];
        preamble_count = tmp_preamble_count;

        input_count = 0;
        while (!$feof(input_fd)) begin
            scan_count = $fscanf(input_fd, "%d %d %d\n", tmp_valid, tmp_i, tmp_q);
            if (scan_count == 3) begin
                if (input_count >= MAX_SAMPLES) begin
                    $display("ERROR: increase MAX_SAMPLES");
                    $fatal(1);
                end
                input_valid_mem[input_count] = tmp_valid[0];
                input_i_mem[input_count] = tmp_i[W-1:0];
                input_q_mem[input_count] = tmp_q[W-1:0];
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
                $display("ERROR: failed to parse expected bit row %0d", expected_bit_count);
                $fatal(1);
            end
        end

        if (expected_bit_count != tmp_expected_bits) begin
            $display(
                "ERROR: metadata bit count %0d does not match expected file count %0d",
                tmp_expected_bits,
                expected_bit_count
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
        "blocks/block_05_fpga_hdl_flow/tb/bpsk_rx_bit_recovery_input_vectors.txt",
        "blocks/block_05_fpga_hdl_flow/tb/bpsk_rx_bit_recovery_expected_bits.txt",
        "blocks/block_05_fpga_hdl_flow/tb/bpsk_rx_bit_recovery_meta.txt"
    );

    $dumpfile("blocks/block_05_fpga_hdl_flow/tb/tb_bpsk_rx_bit_recovery.vcd");
    $dumpvars(0, tb_bpsk_rx_bit_recovery);

    repeat (3) @(posedge clk);
    @(negedge clk);
    rst = 1'b0;

    for (idx = 0; idx < input_count; idx = idx + 1) begin
        @(negedge clk);
        in_valid = input_valid_mem[idx];
        in_i = input_i_mem[idx];
        in_q = input_q_mem[idx];
    end

    @(negedge clk);
    in_valid = 1'b0;
    in_i = '0;
    in_q = '0;

    for (wait_cycles = 0; wait_cycles < MAX_WAIT_CYCLES && recovered_count < expected_bit_count; wait_cycles = wait_cycles + 1) begin
        @(posedge clk);
    end

    if (recovered_count != expected_bit_count) begin
        $display(
            "ERROR: recovered %0d bits, expected %0d",
            recovered_count,
            expected_bit_count
        );
        $fatal(1);
    end

    repeat (3) @(posedge clk);

    if (total_errors == 0) begin
        $display(
            "PASS: bpsk_rx_bit_recovery completed without errors (%0d bits, payload errors %0d)",
            expected_bit_count,
            payload_errors
        );
        $finish;
    end else begin
        $display(
            "FAIL: bpsk_rx_bit_recovery completed with total/payload errors = %0d / %0d",
            total_errors,
            payload_errors
        );
        $fatal(1);
    end
end

always @(posedge clk) begin
    if (!rst && bit_valid) begin
        if (recovered_count >= expected_bit_count) begin
            $display("ERROR at %0t: unexpected extra recovered bit %0b", $time, bit_out);
            total_errors = total_errors + 1;
        end else begin
            if (!expected_valid_mem[recovered_count]) begin
                $display("ERROR at %0t: expected bit %0d is marked invalid", $time, recovered_count);
                total_errors = total_errors + 1;
            end else if (bit_out !== expected_bit_mem[recovered_count]) begin
                $display(
                    "ERROR at %0t: recovered bit=%0b expected=%0b index=%0d",
                    $time,
                    bit_out,
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
