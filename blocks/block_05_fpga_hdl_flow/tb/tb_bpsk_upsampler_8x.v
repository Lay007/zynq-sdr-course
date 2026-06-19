// Lab 5.7 - self-checking testbench for bpsk_upsampler_8x
//
// Replays the symbol-rate BPSK stream from the shared Block 11 package and
// verifies the continuous 8x zero-stuffed output sequence sample-by-sample.

`timescale 1ns/1ps

module tb_bpsk_upsampler_8x;

localparam integer W = 16;
localparam integer MAX_SYMBOLS = 512;
localparam integer MAX_SAMPLES = 4096;
localparam integer CLK_PERIOD_NS = 10;

reg clk = 1'b0;
reg rst = 1'b1;
reg in_valid = 1'b0;
reg signed [W-1:0] in_i = '0;
reg signed [W-1:0] in_q = '0;

wire in_ready;
wire out_valid;
wire signed [W-1:0] out_i;
wire signed [W-1:0] out_q;

reg signed [W-1:0] symbol_i [0:MAX_SYMBOLS-1];
reg signed [W-1:0] symbol_q [0:MAX_SYMBOLS-1];
reg expected_valid [0:MAX_SAMPLES-1];
reg signed [W-1:0] expected_i [0:MAX_SAMPLES-1];
reg signed [W-1:0] expected_q [0:MAX_SAMPLES-1];

integer symbol_count = 0;
integer sample_count = 0;
integer symbol_idx = 0;
integer expected_idx = 0;
integer errors = 0;
reg stream_started = 1'b0;

integer input_fd;
integer expected_fd;
integer scan_count_input;
integer scan_count_expected;
integer tmp_i_input;
integer tmp_q_input;
integer tmp_valid_expected;
integer tmp_i_expected;
integer tmp_q_expected;
reg [1023:0] line;

bpsk_upsampler_8x #(
    .W(W),
    .SPS(8),
    .PHASE_W(3)
) dut (
    .clk(clk),
    .rst(rst),
    .in_valid(in_valid),
    .in_i(in_i),
    .in_q(in_q),
    .in_ready(in_ready),
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

        symbol_count = 0;
        while (!$feof(input_fd)) begin
            scan_count_input = $fscanf(input_fd, "%d %d\n", tmp_i_input, tmp_q_input);
            if (scan_count_input == 2) begin
                if (symbol_count >= MAX_SYMBOLS) begin
                    $display("ERROR: increase MAX_SYMBOLS");
                    $fatal(1);
                end
                symbol_i[symbol_count] = tmp_i_input[W-1:0];
                symbol_q[symbol_count] = tmp_q_input[W-1:0];
                symbol_count = symbol_count + 1;
            end else if (scan_count_input != -1) begin
                $display("ERROR: failed to parse symbol row %0d", symbol_count);
                $fatal(1);
            end
        end

        sample_count = 0;
        while (!$feof(expected_fd)) begin
            scan_count_expected = $fscanf(expected_fd, "%d %d %d\n", tmp_valid_expected, tmp_i_expected, tmp_q_expected);
            if (scan_count_expected == 3) begin
                if (sample_count >= MAX_SAMPLES) begin
                    $display("ERROR: increase MAX_SAMPLES");
                    $fatal(1);
                end
                expected_valid[sample_count] = tmp_valid_expected[0];
                expected_i[sample_count] = tmp_i_expected[W-1:0];
                expected_q[sample_count] = tmp_q_expected[W-1:0];
                sample_count = sample_count + 1;
            end else if (scan_count_expected != -1) begin
                $display("ERROR: failed to parse expected row %0d", sample_count);
                $fatal(1);
            end
        end

        $fclose(input_fd);
        $fclose(expected_fd);
    end
endtask

initial begin
    read_vectors(
        "blocks/block_05_fpga_hdl_flow/tb/bpsk_upsampler_8x_input_vectors.txt",
        "blocks/block_05_fpga_hdl_flow/tb/bpsk_upsampler_8x_expected_vectors.txt"
    );

    $dumpfile("blocks/block_05_fpga_hdl_flow/tb/tb_bpsk_upsampler_8x.vcd");
    $dumpvars(0, tb_bpsk_upsampler_8x);

    repeat (3) @(posedge clk);
    @(negedge clk);
    rst = 1'b0;

    while (symbol_idx < symbol_count) begin
        @(negedge clk);
        if (in_ready) begin
            in_valid = 1'b1;
            in_i = symbol_i[symbol_idx];
            in_q = symbol_q[symbol_idx];
            symbol_idx = symbol_idx + 1;
        end else begin
            in_valid = 1'b0;
            in_i = '0;
            in_q = '0;
        end
    end

    @(negedge clk);
    in_valid = 1'b0;
    in_i = '0;
    in_q = '0;

    wait (expected_idx == sample_count);
    repeat (2) @(posedge clk);

    if (errors == 0) begin
        $display(
            "PASS: bpsk_upsampler_8x test completed without errors (%0d symbols, %0d samples)",
            symbol_count,
            sample_count
        );
        $finish;
    end else begin
        $display("FAIL: bpsk_upsampler_8x test completed with %0d errors", errors);
        $fatal(1);
    end
end

always @(posedge clk) begin
    if (rst) begin
        stream_started <= 1'b0;
    end else begin
        if (!stream_started && out_valid) begin
            stream_started <= 1'b1;
        end
    end

    if (!rst && (stream_started || out_valid) && expected_idx < sample_count) begin
        if (out_valid !== expected_valid[expected_idx]) begin
            $display(
                "ERROR at %0t: out_valid=%0b expected=%0b idx=%0d",
                $time,
                out_valid,
                expected_valid[expected_idx],
                expected_idx
            );
            errors = errors + 1;
        end

        if (expected_valid[expected_idx]) begin
            if (out_i !== expected_i[expected_idx] || out_q !== expected_q[expected_idx]) begin
                $display(
                    "ERROR at %0t: out=(%0d,%0d) expected=(%0d,%0d) idx=%0d",
                    $time,
                    out_i,
                    out_q,
                    expected_i[expected_idx],
                    expected_q[expected_idx],
                    expected_idx
                );
                errors = errors + 1;
            end
        end

        expected_idx = expected_idx + 1;
    end
end

endmodule
