// Lab 5.13b - integration check for the runtime fixed/Gardner timing mux.

`timescale 1ns/1ps

module tb_qpsk_timing_recovery_mux;

localparam integer W = 16;
localparam integer N_RX = 1702;
localparam integer N_SYM = 140;

reg clk = 1'b0;
reg rst = 1'b1;
reg in_valid = 1'b0;
reg signed [W-1:0] in_i = 0;
reg signed [W-1:0] in_q = 0;
reg [31:0] rx_mem [0:N_RX-1];
reg frame_bits [0:511];
integer index;
integer loop_count;
integer fixed_count;
integer loop_errors;
integer fixed_errors;

wire loop_valid;
wire [1:0] loop_dibit;
wire fixed_valid;
wire [1:0] fixed_dibit;

qpsk_rx_bit_recovery_chain #(
    .W(W), .SPS(8), .INDEX_W(16), .TIMING_RECOVERY_ENABLE(1)
) loop_rx (
    .clk(clk), .rst(rst), .rst_carrier(rst),
    .dc_block_en(1'b0), .costas_en(1'b0), .coarse_cfo_en(1'b0),
    .phase_pick_en(1'b0), .timing_recovery_en(1'b1),
    .in_valid(in_valid), .in_i(in_i), .in_q(in_q),
    .start_offset(16'd63), .symbol_count(N_SYM[15:0]),
    .out_valid(loop_valid), .out_dibit(loop_dibit),
    .debug_symbol_valid(), .debug_symbol_i(), .debug_symbol_q(),
    .cfo_ready(), .cfo_omega(), .timing_mu(), .timing_omega(), .timing_error()
);

qpsk_rx_bit_recovery_chain #(
    .W(W), .SPS(8), .INDEX_W(16), .TIMING_RECOVERY_ENABLE(1)
) fixed_rx (
    .clk(clk), .rst(rst), .rst_carrier(rst),
    .dc_block_en(1'b0), .costas_en(1'b0), .coarse_cfo_en(1'b0),
    .phase_pick_en(1'b0), .timing_recovery_en(1'b0),
    .in_valid(in_valid), .in_i(in_i), .in_q(in_q),
    .start_offset(16'd68), .symbol_count(N_SYM[15:0]),
    .out_valid(fixed_valid), .out_dibit(fixed_dibit),
    .debug_symbol_valid(), .debug_symbol_i(), .debug_symbol_q(),
    .cfo_ready(), .cfo_omega(), .timing_mu(), .timing_omega(), .timing_error()
);

always #5 clk = ~clk;

always @(posedge clk) begin
    if (!rst && loop_valid && loop_count < N_SYM) begin
        if (loop_dibit[0] !== frame_bits[2*loop_count]) loop_errors = loop_errors + 1;
        if (loop_dibit[1] !== frame_bits[2*loop_count+1]) loop_errors = loop_errors + 1;
        loop_count = loop_count + 1;
    end
    if (!rst && fixed_valid && fixed_count < N_SYM) begin
        if (fixed_dibit[0] !== frame_bits[2*fixed_count]) fixed_errors = fixed_errors + 1;
        if (fixed_dibit[1] !== frame_bits[2*fixed_count+1]) fixed_errors = fixed_errors + 1;
        fixed_count = fixed_count + 1;
    end
end

initial begin
    $readmemh("blocks/block_05_fpga_hdl_flow/tb/qpsk_chain_drift_rx.mem", rx_mem);
    $readmemh("blocks/block_05_fpga_hdl_flow/rtl/bpsk_frame_bits.mem", frame_bits);
    loop_count = 0;
    fixed_count = 0;
    loop_errors = 0;
    fixed_errors = 0;

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
        "QPSK runtime timing mux: Gardner %0d symbols %0d/280 errors; fixed %0d symbols %0d/280 errors",
        loop_count, loop_errors, fixed_count, fixed_errors
    );
    if (loop_count != N_SYM || loop_errors != 0) begin
        $display("FAIL: integrated Gardner path did not recover the drifted frame");
        $fatal(1);
    end
    if (fixed_count != N_SYM || fixed_errors == 0) begin
        $display("FAIL: runtime fixed-phase control did not retain its drift floor");
        $fatal(1);
    end
    $display("PASS: runtime timing mux selects continuous recovery without changing the baseline path");
    $finish;
end

endmodule
