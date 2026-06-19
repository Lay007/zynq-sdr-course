// Lab 5.6 - self-checking testbench for bpsk_rrc_tx_fir
//
// Replays the deterministic BPSK symbol stream derived from the shared
// Block 11 package and verifies the pulse-shaped Q1.15 output sample-by-sample.

`timescale 1ns/1ps

module tb_bpsk_rrc_tx_fir;

localparam integer W = 16;
localparam integer MAX_VECTORS = 4096;
localparam integer CLK_PERIOD_NS = 10;

reg clk = 1'b0;
reg rst = 1'b1;
reg in_valid = 1'b0;
reg signed [W-1:0] in_i = '0;
reg signed [W-1:0] in_q = '0;

wire out_valid;
wire signed [W-1:0] out_i;
wire signed [W-1:0] out_q;

reg vector_valid [0:MAX_VECTORS-1];
reg signed [W-1:0] vector_i [0:MAX_VECTORS-1];
reg signed [W-1:0] vector_q [0:MAX_VECTORS-1];

reg expected_valid [0:MAX_VECTORS-1];
reg signed [W-1:0] expected_i [0:MAX_VECTORS-1];
reg signed [W-1:0] expected_q [0:MAX_VECTORS-1];

reg expected_valid_current = 1'b0;
reg signed [W-1:0] expected_i_current = '0;
reg signed [W-1:0] expected_q_current = '0;

reg expected_valid_d1 = 1'b0;
reg signed [W-1:0] expected_i_d1 = '0;
reg signed [W-1:0] expected_q_d1 = '0;

integer idx;
integer errors = 0;
integer vector_count = 0;
integer input_fd;
integer expected_fd;
integer scan_count_input;
integer scan_count_expected;
integer tmp_valid_input;
integer tmp_i_input;
integer tmp_q_input;
integer tmp_valid_expected;
integer tmp_i_expected;
integer tmp_q_expected;
reg [1023:0] line;

bpsk_rrc_tx_fir #(
    .W(W)
) dut (
    .clk(clk),
    .rst(rst),
    .in_valid(in_valid),
    .in_i(in_i),
    .in_q(in_q),
    .out_valid(out_valid),
    .out_i(out_i),
    .out_q(out_q)
);

always #(CLK_PERIOD_NS/2) clk = ~clk;

task read_vectors;
    input [1023:0] input_path;
    input [1023:0] expected_path;
    begin
        input_fd = $fopen(input_path, "r");
        if (input_fd == 0) begin
            $display("ERROR: cannot open input vector file");
            $fatal(1);
        end

        expected_fd = $fopen(expected_path, "r");
        if (expected_fd == 0) begin
            $display("ERROR: cannot open expected vector file");
            $fatal(1);
        end

        scan_count_input = $fgets(line, input_fd);
        scan_count_expected = $fgets(line, expected_fd);
        vector_count = 0;

        while (!$feof(input_fd) && !$feof(expected_fd)) begin
            scan_count_input = $fscanf(input_fd, "%d %d %d\n", tmp_valid_input, tmp_i_input, tmp_q_input);
            scan_count_expected = $fscanf(expected_fd, "%d %d %d\n", tmp_valid_expected, tmp_i_expected, tmp_q_expected);

            if (scan_count_input == 3 && scan_count_expected == 3) begin
                if (vector_count >= MAX_VECTORS) begin
                    $display("ERROR: increase MAX_VECTORS");
                    $fatal(1);
                end

                vector_valid[vector_count] = tmp_valid_input[0];
                vector_i[vector_count] = tmp_i_input[W-1:0];
                vector_q[vector_count] = tmp_q_input[W-1:0];

                expected_valid[vector_count] = tmp_valid_expected[0];
                expected_i[vector_count] = tmp_i_expected[W-1:0];
                expected_q[vector_count] = tmp_q_expected[W-1:0];
                vector_count = vector_count + 1;
            end else if (scan_count_input != -1 || scan_count_expected != -1) begin
                $display("ERROR: failed to parse vector row %0d", vector_count);
                $fatal(1);
            end
        end

        $fclose(input_fd);
        $fclose(expected_fd);
    end
endtask

initial begin
    read_vectors(
        "blocks/block_05_fpga_hdl_flow/tb/bpsk_rrc_tx_fir_input_vectors.txt",
        "blocks/block_05_fpga_hdl_flow/tb/bpsk_rrc_tx_fir_expected_vectors.txt"
    );

    $dumpfile("blocks/block_05_fpga_hdl_flow/tb/tb_bpsk_rrc_tx_fir.vcd");
    $dumpvars(0, tb_bpsk_rrc_tx_fir);

    repeat (3) @(posedge clk);
    @(negedge clk);
    rst = 1'b0;

    for (idx = 0; idx < vector_count; idx = idx + 1) begin
        @(negedge clk);
        in_valid = vector_valid[idx];
        in_i = vector_i[idx];
        in_q = vector_q[idx];
        expected_valid_current = expected_valid[idx];
        expected_i_current = expected_i[idx];
        expected_q_current = expected_q[idx];
    end

    @(negedge clk);
    in_valid = 1'b0;
    in_i = '0;
    in_q = '0;
    expected_valid_current = 1'b0;
    expected_i_current = '0;
    expected_q_current = '0;

    repeat (4) @(posedge clk);

    if (errors == 0) begin
        $display("PASS: bpsk_rrc_tx_fir test completed without errors (%0d vectors)", vector_count);
        $finish;
    end else begin
        $display("FAIL: bpsk_rrc_tx_fir test completed with %0d errors", errors);
        $fatal(1);
    end
end

always @(posedge clk) begin
    if (rst) begin
        expected_valid_d1 <= 1'b0;
        expected_i_d1 <= '0;
        expected_q_d1 <= '0;
    end else begin
        if (out_valid !== expected_valid_d1) begin
            $display("ERROR at %0t: out_valid=%0b expected=%0b", $time, out_valid, expected_valid_d1);
            errors = errors + 1;
        end

        if (expected_valid_d1) begin
            if (out_i !== expected_i_d1 || out_q !== expected_q_d1) begin
                $display(
                    "ERROR at %0t: out=(%0d,%0d) expected=(%0d,%0d)",
                    $time, out_i, out_q, expected_i_d1, expected_q_d1
                );
                errors = errors + 1;
            end
        end

        expected_valid_d1 <= expected_valid_current;
        expected_i_d1 <= expected_i_current;
        expected_q_d1 <= expected_q_current;
    end
end

endmodule
