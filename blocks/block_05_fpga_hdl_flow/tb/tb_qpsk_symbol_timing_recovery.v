// Lab 5.13b - bit-exact QPSK Gardner timing-recovery check.

`timescale 1ns/1ps

module tb_qpsk_symbol_timing_recovery;

localparam integer W = 16;
localparam integer N_MF = 1254;
localparam integer N_SYM = 140;
localparam integer START_OFFSET = 63;

reg clk = 1'b0;
reg rst = 1'b1;
reg in_valid = 1'b0;
reg signed [W-1:0] in_i = 0;
reg signed [W-1:0] in_q = 0;
reg [31:0] input_mem [0:N_MF-1];
reg [31:0] expected_mem [0:N_SYM-1];

wire out_valid;
wire signed [W-1:0] out_i;
wire signed [W-1:0] out_q;
wire [15:0] timing_mu;
wire signed [16:0] timing_omega;
wire signed [2:0] timing_error;

integer index;
integer captured;
integer mismatches;

qpsk_symbol_timing_recovery #(
    .W(W),
    .SPS(8),
    .INDEX_W(16)
) dut (
    .clk(clk),
    .rst(rst),
    .in_valid(in_valid),
    .in_i(in_i),
    .in_q(in_q),
    .start_offset(START_OFFSET[15:0]),
    .symbol_count(N_SYM[15:0]),
    .out_valid(out_valid),
    .out_i(out_i),
    .out_q(out_q),
    .timing_mu(timing_mu),
    .timing_omega(timing_omega),
    .timing_error(timing_error)
);

always #5 clk = ~clk;

always @(posedge clk) begin
    if (!rst && out_valid) begin
        if (captured >= N_SYM) begin
            $display("FAIL: timing recovery emitted more than %0d symbols", N_SYM);
            mismatches = mismatches + 1;
        end else if ({out_i, out_q} !== expected_mem[captured]) begin
            $display(
                "FAIL: symbol %0d got %04x_%04x expected %08x",
                captured, out_i, out_q, expected_mem[captured]
            );
            mismatches = mismatches + 1;
        end
        captured = captured + 1;
    end
end

initial begin
    $readmemh("blocks/block_05_fpga_hdl_flow/tb/qpsk_timing_recovery_mf_input.mem", input_mem);
    $readmemh("blocks/block_05_fpga_hdl_flow/tb/qpsk_timing_recovery_expected.mem", expected_mem);
    captured = 0;
    mismatches = 0;

    repeat (4) @(negedge clk);
    rst = 1'b0;
    for (index = 0; index < N_MF; index = index + 1) begin
        @(negedge clk);
        in_valid = 1'b1;
        in_i = input_mem[index][31:16];
        in_q = input_mem[index][15:0];
    end
    @(negedge clk);
    in_valid = 1'b0;
    repeat (20) @(posedge clk);

    if (captured != N_SYM) begin
        $display("FAIL: recovered %0d/%0d symbols", captured, N_SYM);
        $fatal(1);
    end
    if (mismatches != 0) begin
        $display("FAIL: %0d QPSK timing-recovery mismatches", mismatches);
        $fatal(1);
    end
    $display(
        "PASS: QPSK Gardner RTL matches the fixed model for %0d symbols at SPS=8.06; omega=%0d mu=%0d",
        captured, timing_omega, timing_mu
    );
    $finish;
end

endmodule
