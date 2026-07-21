// Lab 5.13b - full QPSK RX comparison on a time-drifted SPS=8.06 frame.
// The continuous Gardner loop must recover all 280 bits; the best fixed phase
// for the same waveform must accumulate errors as its sample point drifts.

`timescale 1ns/1ps

module tb_qpsk_timing_recovery_chain;

localparam integer W = 16;
localparam integer N_RX = 1702;
localparam integer N_SYM = 140;
localparam integer TR_OFFSET = 65;
localparam integer FP_OFFSET = 68;

reg clk = 1'b0;
reg rst = 1'b1;
reg in_valid = 1'b0;
reg signed [W-1:0] in_i = 0;
reg signed [W-1:0] in_q = 0;
reg [31:0] rx_mem [0:N_RX-1];
reg frame_bits [0:511];
integer index;
integer tr_count;
integer fp_count;
integer tr_errors;
integer fp_errors;

wire tr_mf_valid;
wire signed [W-1:0] tr_mf_i;
wire signed [W-1:0] tr_mf_q;
wire fp_mf_valid;
wire signed [W-1:0] fp_mf_i;
wire signed [W-1:0] fp_mf_q;

bpsk_rrc_rx_fir tr_mf (
    .clk(clk), .rst(rst), .in_valid(in_valid), .in_i(in_i), .in_q(in_q),
    .out_valid(tr_mf_valid), .out_i(tr_mf_i), .out_q(tr_mf_q)
);
bpsk_rrc_rx_fir fp_mf (
    .clk(clk), .rst(rst), .in_valid(in_valid), .in_i(in_i), .in_q(in_q),
    .out_valid(fp_mf_valid), .out_i(fp_mf_i), .out_q(fp_mf_q)
);

wire tr_valid;
wire signed [W-1:0] tr_i;
wire signed [W-1:0] tr_q;
qpsk_symbol_timing_recovery #(.W(W), .SPS(8), .INDEX_W(16)) timing_loop (
    .clk(clk), .rst(rst), .in_valid(tr_mf_valid), .in_i(tr_mf_i), .in_q(tr_mf_q),
    .start_offset(TR_OFFSET[15:0]), .symbol_count(N_SYM[15:0]),
    .out_valid(tr_valid), .out_i(tr_i), .out_q(tr_q),
    .timing_mu(), .timing_omega(), .timing_error()
);

wire fp_valid;
wire signed [W-1:0] fp_i;
wire signed [W-1:0] fp_q;
bpsk_symbol_timing_sampler #(.W(W), .SPS(8), .INDEX_W(16)) fixed_sampler (
    .clk(clk), .rst(rst), .in_valid(fp_mf_valid), .in_i(fp_mf_i), .in_q(fp_mf_q),
    .start_offset(FP_OFFSET[15:0]), .symbol_count(N_SYM[15:0]),
    .out_valid(fp_valid), .out_i(fp_i), .out_q(fp_q)
);

wire tr_dec_valid;
wire [1:0] tr_dibit;
wire fp_dec_valid;
wire [1:0] fp_dibit;
qpsk_hard_decision tr_decision (
    .clk(clk), .rst(rst), .in_valid(tr_valid), .in_i(tr_i), .in_q(tr_q),
    .out_valid(tr_dec_valid), .out_dibit(tr_dibit)
);
qpsk_hard_decision fp_decision (
    .clk(clk), .rst(rst), .in_valid(fp_valid), .in_i(fp_i), .in_q(fp_q),
    .out_valid(fp_dec_valid), .out_dibit(fp_dibit)
);

always #5 clk = ~clk;

always @(posedge clk) begin
    if (!rst && tr_dec_valid && tr_count < N_SYM) begin
        if (tr_dibit[0] !== frame_bits[2*tr_count]) tr_errors = tr_errors + 1;
        if (tr_dibit[1] !== frame_bits[2*tr_count+1]) tr_errors = tr_errors + 1;
        tr_count = tr_count + 1;
    end
    if (!rst && fp_dec_valid && fp_count < N_SYM) begin
        if (fp_dibit[0] !== frame_bits[2*fp_count]) fp_errors = fp_errors + 1;
        if (fp_dibit[1] !== frame_bits[2*fp_count+1]) fp_errors = fp_errors + 1;
        fp_count = fp_count + 1;
    end
end

initial begin
    $readmemh("blocks/block_05_fpga_hdl_flow/tb/qpsk_chain_drift_rx.mem", rx_mem);
    $readmemh("blocks/block_05_fpga_hdl_flow/rtl/bpsk_frame_bits.mem", frame_bits);
    tr_count = 0;
    fp_count = 0;
    tr_errors = 0;
    fp_errors = 0;

    repeat (4) @(negedge clk);
    rst = 1'b0;
    for (index = 0; index < N_RX; index = index + 1) begin
        @(negedge clk);
        in_valid = 1'b1;
        in_i = rx_mem[index][31:16];
        in_q = rx_mem[index][15:0];
    end
    @(negedge clk);
    in_valid = 1'b0;
    repeat (40) @(posedge clk);

    $display(
        "QPSK timing chain: Gardner %0d/%0d symbols, %0d/280 errors; fixed phase %0d/%0d, %0d/280 errors",
        tr_count, N_SYM, tr_errors, fp_count, N_SYM, fp_errors
    );
    if (tr_count != N_SYM || tr_errors != 0) begin
        $display("FAIL: continuous QPSK timing recovery did not reach BER=0");
        $fatal(1);
    end
    if (fp_count != N_SYM || fp_errors == 0) begin
        $display("FAIL: fixed-phase control did not expose the injected timing drift");
        $fatal(1);
    end
    $display("PASS: continuous QPSK timing recovery removes the SPS=8.06 drift floor");
    $finish;
end

endmodule
