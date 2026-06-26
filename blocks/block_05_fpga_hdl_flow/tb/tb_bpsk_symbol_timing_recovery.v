// Lab 5.8b - bit-exact check of bpsk_symbol_timing_recovery against the validated
// fixed-point model. Feeds a time-drifted (SPS=8.03) matched-filter vector and
// requires the HDL hard decisions to match the model's recovered bits exactly.

`timescale 1ns/1ps

module tb_bpsk_symbol_timing_recovery;

localparam integer W = 16;
localparam integer N_MF = 2382;
localparam integer N_SYM = 281;
localparam integer START_OFF = 64;

reg clk = 1'b0;
reg rst = 1'b1;
reg in_valid = 1'b0;
reg signed [W-1:0] in_i = 0;

wire out_valid;
wire signed [W-1:0] out_i;
wire signed [W-1:0] out_q;

reg signed [W-1:0] mf_mem [0:N_MF-1];
reg model_bits [0:N_SYM-1];
reg captured [0:N_SYM-1];

integer k, cap_count, mismatches, i;

bpsk_symbol_timing_recovery #(
    .W(W), .SPS(8), .INDEX_W(16)
) dut (
    .clk(clk),
    .rst(rst),
    .in_valid(in_valid),
    .in_i(in_i),
    .in_q(16'sd0),
    .start_offset(START_OFF[15:0]),
    .symbol_count(N_SYM[15:0]),
    .out_valid(out_valid),
    .out_i(out_i),
    .out_q(out_q)
);

always #5 clk = ~clk;

always @(posedge clk) begin
    if (!rst && out_valid) begin
        if (cap_count < N_SYM) begin
            captured[cap_count] <= (out_i < 0);
        end
        cap_count <= cap_count + 1;
    end
end

initial begin
    $readmemh("blocks/block_05_fpga_hdl_flow/tb/bpsk_timing_recovery_mf_input.mem", mf_mem);
    $readmemb("blocks/block_05_fpga_hdl_flow/tb/bpsk_timing_recovery_model_bits.txt", model_bits);
    cap_count = 0;

    repeat (3) @(negedge clk);
    rst = 1'b0;

    for (k = 0; k < N_MF; k = k + 1) begin
        @(negedge clk);
        in_valid = 1'b1;
        in_i = mf_mem[k];
    end
    @(negedge clk);
    in_valid = 1'b0;
    repeat (20) @(posedge clk);

    if (cap_count < N_SYM) begin
        $display("FAIL: only %0d/%0d symbols recovered", cap_count, N_SYM);
        $fatal(1);
    end
    mismatches = 0;
    for (i = 0; i < N_SYM; i = i + 1) begin
        if (captured[i] !== model_bits[i]) begin
            mismatches = mismatches + 1;
        end
    end
    if (mismatches != 0) begin
        $display("FAIL: %0d/%0d HDL bits differ from fixed-point model", mismatches, N_SYM);
        $fatal(1);
    end
    $display("PASS: bpsk_symbol_timing_recovery matches fixed-point model bit-exactly (%0d symbols, SPS=8.03 drift)", cap_count);
    $finish;
end

endmodule
