// Lab 5.1 — self-checking testbench for iq_passthrough
//
// Runs a small deterministic vector set and verifies one-cycle latency.
// Intended for Icarus Verilog in CI and for local educational simulation.

`timescale 1ns/1ps

module tb_iq_passthrough;

localparam integer W = 16;
localparam integer NUM_VECTORS = 8;
localparam integer CLK_PERIOD_NS = 10;

reg clk = 1'b0;
reg rst = 1'b1;
reg in_valid = 1'b0;
reg signed [W-1:0] in_i = 0;
reg signed [W-1:0] in_q = 0;

wire out_valid;
wire signed [W-1:0] out_i;
wire signed [W-1:0] out_q;

reg vector_valid [0:NUM_VECTORS-1];
reg signed [W-1:0] vector_i [0:NUM_VECTORS-1];
reg signed [W-1:0] vector_q [0:NUM_VECTORS-1];

reg expected_valid_d1 = 1'b0;
reg signed [W-1:0] expected_i_d1 = 0;
reg signed [W-1:0] expected_q_d1 = 0;

integer idx;
integer errors = 0;

iq_passthrough #(
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

initial begin
    vector_valid[0] = 1'b1; vector_i[0] =  16'sd32767; vector_q[0] =      16'sd0;
    vector_valid[1] = 1'b1; vector_i[1] =      16'sd0; vector_q[1] =  16'sd32767;
    vector_valid[2] = 1'b1; vector_i[2] = -16'sd32768; vector_q[2] =      16'sd0;
    vector_valid[3] = 1'b0; vector_i[3] =      16'sd0; vector_q[3] =      16'sd0;
    vector_valid[4] = 1'b1; vector_i[4] =   16'sd1234; vector_q[4] =  -16'sd5678;
    vector_valid[5] = 1'b1; vector_i[5] =  -16'sd2222; vector_q[5] =   16'sd3333;
    vector_valid[6] = 1'b0; vector_i[6] =      16'sd0; vector_q[6] =      16'sd0;
    vector_valid[7] = 1'b1; vector_i[7] =     16'sd42; vector_q[7] =    -16'sd42;
end

initial begin
    $dumpfile("tb_iq_passthrough.vcd");
    $dumpvars(0, tb_iq_passthrough);

    repeat (3) @(posedge clk);
    rst <= 1'b0;

    for (idx = 0; idx < NUM_VECTORS; idx = idx + 1) begin
        @(posedge clk);
        in_valid <= vector_valid[idx];
        in_i <= vector_i[idx];
        in_q <= vector_q[idx];
    end

    @(posedge clk);
    in_valid <= 1'b0;
    in_i <= 0;
    in_q <= 0;

    repeat (3) @(posedge clk);

    if (errors == 0) begin
        $display("PASS: iq_passthrough test completed without errors");
        $finish;
    end else begin
        $display("FAIL: iq_passthrough test completed with %0d errors", errors);
        $fatal(1);
    end
end

always @(posedge clk) begin
    if (rst) begin
        expected_valid_d1 <= 1'b0;
        expected_i_d1 <= 0;
        expected_q_d1 <= 0;
    end else begin
        if (out_valid !== expected_valid_d1) begin
            $display("ERROR at %0t: out_valid=%0b expected=%0b", $time, out_valid, expected_valid_d1);
            errors = errors + 1;
        end

        if (expected_valid_d1) begin
            if (out_i !== expected_i_d1 || out_q !== expected_q_d1) begin
                $display("ERROR at %0t: out=(%0d,%0d) expected=(%0d,%0d)",
                         $time, out_i, out_q, expected_i_d1, expected_q_d1);
                errors = errors + 1;
            end
        end

        expected_valid_d1 <= in_valid;
        expected_i_d1 <= in_i;
        expected_q_d1 <= in_q;
    end
end

endmodule
