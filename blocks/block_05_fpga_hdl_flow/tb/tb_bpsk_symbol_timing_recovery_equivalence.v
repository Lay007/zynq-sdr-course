// Lab 5.8b - equivalence of the two schedules of bpsk_symbol_timing_recovery.
//
// PIPELINED=0 (one-clock loop) and PIPELINED=1 (interpolation and timing error
// one clock after the strobe, lookahead loop filter) get the same drifted
// matched-filter stream. Every output symbol must match in I and Q, in the same
// order; only the output clock may differ. GAPS=1 drops in_valid at random, so
// the clock after a strobe sometimes carries a sample and sometimes does not.
// The Q input carries a second, unrelated sequence so the Q path is checked too.

`timescale 1ns/1ps

module tb_bpsk_symbol_timing_recovery_equivalence;

// GAPS=0 feeds a sample every clock; the default keeps random idle clocks.
parameter integer GAPS = 1;

localparam integer W = 16;
localparam integer N_MF = 2382;
localparam integer N_SYM = 281;
localparam integer START_OFF = 64;

reg clk = 1'b0;
reg rst = 1'b1;
reg in_valid = 1'b0;
reg signed [W-1:0] in_i = 0;
reg signed [W-1:0] in_q = 0;

wire ref_valid;
wire signed [W-1:0] ref_i;
wire signed [W-1:0] ref_q;
wire pipe_valid;
wire signed [W-1:0] pipe_i;
wire signed [W-1:0] pipe_q;

reg signed [W-1:0] mf_mem [0:N_MF-1];
reg signed [W-1:0] ref_i_log [0:N_SYM-1];
reg signed [W-1:0] ref_q_log [0:N_SYM-1];
reg signed [W-1:0] pipe_i_log [0:N_SYM-1];
reg signed [W-1:0] pipe_q_log [0:N_SYM-1];

integer k, ref_count, pipe_count, mismatches, idle_cycles, seed;

bpsk_symbol_timing_recovery #(
    .W(W), .SPS(8), .INDEX_W(16), .PIPELINED(0)
) reference (
    .clk(clk), .rst(rst), .in_valid(in_valid), .in_i(in_i), .in_q(in_q),
    .start_offset(START_OFF[15:0]), .symbol_count(N_SYM[15:0]),
    .out_valid(ref_valid), .out_i(ref_i), .out_q(ref_q)
);

bpsk_symbol_timing_recovery #(
    .W(W), .SPS(8), .INDEX_W(16), .PIPELINED(1)
) pipelined (
    .clk(clk), .rst(rst), .in_valid(in_valid), .in_i(in_i), .in_q(in_q),
    .start_offset(START_OFF[15:0]), .symbol_count(N_SYM[15:0]),
    .out_valid(pipe_valid), .out_i(pipe_i), .out_q(pipe_q)
);

always #5 clk = ~clk;

always @(posedge clk) begin
    if (!rst && ref_valid) begin
        if (ref_count < N_SYM) begin
            ref_i_log[ref_count] = ref_i;
            ref_q_log[ref_count] = ref_q;
        end
        ref_count = ref_count + 1;
    end
    if (!rst && pipe_valid) begin
        if (pipe_count < N_SYM) begin
            pipe_i_log[pipe_count] = pipe_i;
            pipe_q_log[pipe_count] = pipe_q;
        end
        pipe_count = pipe_count + 1;
    end
end

initial begin
    $readmemh("blocks/block_05_fpga_hdl_flow/tb/bpsk_timing_recovery_mf_input.mem", mf_mem);
    ref_count = 0;
    pipe_count = 0;
    mismatches = 0;
    idle_cycles = 0;
    seed = 32'h5EED;

    repeat (3) @(negedge clk);
    rst = 1'b0;

    for (k = 0; k < N_MF; k = k + 1) begin
        if (GAPS != 0) begin
            while (($random(seed) & 3) == 0) begin
                @(negedge clk);
                in_valid = 1'b0;
                idle_cycles = idle_cycles + 1;
            end
        end
        @(negedge clk);
        in_valid = 1'b1;
        in_i = mf_mem[k];
        in_q = mf_mem[(k * 7 + 13) % N_MF] >>> 1;
    end
    @(negedge clk);
    in_valid = 1'b0;
    repeat (20) @(posedge clk);

    if (ref_count != N_SYM || pipe_count != N_SYM) begin
        $display("FAIL: symbol counts reference=%0d pipelined=%0d, expected %0d", ref_count, pipe_count, N_SYM);
        $fatal(1);
    end
    for (k = 0; k < N_SYM; k = k + 1) begin
        if (ref_i_log[k] !== pipe_i_log[k] || ref_q_log[k] !== pipe_q_log[k]) begin
            if (mismatches < 5)
                $display("FAIL: symbol %0d reference=(%0d,%0d) pipelined=(%0d,%0d)",
                         k, ref_i_log[k], ref_q_log[k], pipe_i_log[k], pipe_q_log[k]);
            mismatches = mismatches + 1;
        end
    end
    if (mismatches != 0) begin
        $display("FAIL: %0d/%0d symbols differ between PIPELINED=0 and PIPELINED=1", mismatches, N_SYM);
        $fatal(1);
    end
    $display("PASS: bpsk_symbol_timing_recovery PIPELINED=1 equals PIPELINED=0 on all %0d symbols (I and Q values, %0d idle input clocks)",
             N_SYM, idle_cycles);
    $finish;
end

endmodule
