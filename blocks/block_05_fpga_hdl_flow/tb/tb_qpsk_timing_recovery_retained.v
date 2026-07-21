// Lab 5.13b / Lab 11.34 - continuous timing recovery on the retained
// +30 kHz two-board BRAM capture used by the residual-CFO regression.

`timescale 1ns/1ps

module tb_qpsk_timing_recovery_retained;

localparam integer W = 16;
localparam integer INDEX_W = 16;
localparam integer N_SAMPLES = 2600;
localparam integer FRAME_SYMBOLS = 140;
localparam integer CHAIN_SYMBOLS = 396;

reg clk = 1'b0;
reg rst = 1'b1;
reg in_valid = 1'b0;
reg counter_start = 1'b0;
reg signed [W-1:0] in_i = 0;
reg signed [W-1:0] in_q = 0;
reg [INDEX_W-1:0] start_offset = 0;
reg [31:0] samples [0:N_SAMPLES-1];

wire recovered_valid;
wire [1:0] recovered_dibit;
wire counter_done;
wire [INDEX_W-1:0] received_symbols;
wire [INDEX_W-1:0] bit_errors;

integer sample_index;
integer wait_count;
integer offset;
integer best_errors;
integer best_offset;
integer clean_offsets;
reg done_seen;

qpsk_rx_bit_recovery_chain #(
    .W(W), .SPS(8), .INDEX_W(INDEX_W),
    .COSTAS_KP_LOG_TRACK(7), .COSTAS_ACQ_SYMBOLS(64), .COSTAS_KI_LOG(4),
    .COSTAS_SIG_THRESH(8), .COARSE_ENABLE(1), .TIMING_RECOVERY_ENABLE(1)
) receiver (
    .clk(clk), .rst(rst), .rst_carrier(rst),
    .dc_block_en(1'b1), .costas_en(1'b1), .coarse_cfo_en(1'b1),
    .phase_pick_en(1'b0), .timing_recovery_en(1'b1),
    .in_valid(in_valid), .in_i(in_i), .in_q(in_q),
    .start_offset(start_offset), .symbol_count(CHAIN_SYMBOLS[15:0]),
    .out_valid(recovered_valid), .out_dibit(recovered_dibit),
    .debug_symbol_valid(), .debug_symbol_i(), .debug_symbol_q(),
    .cfo_ready(), .cfo_omega(), .timing_mu(), .timing_omega(), .timing_error()
);

qpsk_ber_counter #(
    .INDEX_W(INDEX_W), .MAX_FRAME_BITS(512), .LOCK_PREAMBLE_BITS(24), .LOCK_ERR_TOL(3)
) counter (
    .clk(clk), .rst(rst), .start(counter_start), .abort(1'b0),
    .symbol_count(FRAME_SYMBOLS[15:0]), .preamble_count(16'd24),
    .in_valid(recovered_valid), .in_dibit(recovered_dibit),
    .busy(), .done(counter_done), .quadrant_swapped(),
    .received_symbols(received_symbols), .total_bit_errors(bit_errors)
);

always #5 clk = ~clk;

always @(posedge clk) begin
    if (rst) done_seen <= 1'b0;
    else if (counter_done) done_seen <= 1'b1;
end

task run_offset(input integer selected_offset);
    begin
        rst = 1'b1;
        in_valid = 1'b0;
        counter_start = 1'b0;
        start_offset = selected_offset[INDEX_W-1:0];
        repeat (3) @(negedge clk);
        rst = 1'b0;
        @(negedge clk);
        counter_start = 1'b1;
        @(negedge clk);
        counter_start = 1'b0;
        for (sample_index = 0; sample_index < N_SAMPLES; sample_index = sample_index + 1) begin
            in_i = samples[sample_index][31:16];
            in_q = samples[sample_index][15:0];
            in_valid = 1'b1;
            @(negedge clk);
        end
        in_valid = 1'b0;
        wait_count = 0;
        while (!done_seen && wait_count < 10000) begin
            @(posedge clk);
            wait_count = wait_count + 1;
        end
        @(posedge clk);
    end
endtask

initial begin
    $readmemh("blocks/block_05_fpga_hdl_flow/tb/qpsk_two_board_residual_cfo_rx.mem", samples);
    best_errors = 99999;
    best_offset = -1;
    clean_offsets = 0;

    for (offset = 0; offset < 8; offset = offset + 1) begin
        run_offset(offset);
        $display(
            "  timing offset=%0d recv=%0d errors=%0d/280",
            offset, received_symbols, bit_errors
        );
        if (received_symbols == FRAME_SYMBOLS && bit_errors < best_errors) begin
            best_errors = bit_errors;
            best_offset = offset;
        end
        if (received_symbols == FRAME_SYMBOLS && bit_errors == 0)
            clean_offsets = clean_offsets + 1;
    end

    if (best_errors != 0) begin
        $display("FAIL: continuous timing recovery regressed the retained two-board capture");
        $fatal(1);
    end
    $display(
        "PASS: continuous timing recovery preserves BER 0/280 on the retained capture; best offset=%0d clean offsets=%0d/8",
        best_offset, clean_offsets
    );
    $finish;
end

endmodule
