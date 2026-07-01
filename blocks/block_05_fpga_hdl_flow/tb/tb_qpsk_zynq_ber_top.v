// Lab 5.10b - self-checking QPSK BER top-level (ideal loopback)
//
// Loops the TX I/Q sample stream straight back into RX and sweeps start_offset to
// find the sampling phase that recovers the frame; passes if any offset yields a
// full frame at bit-error-rate 0. This is the QPSK analogue of tb_bpsk_zynq_ber_top.

`timescale 1ns/1ps

module tb_qpsk_zynq_ber_top;

localparam integer W = 16;
localparam integer INDEX_W = 16;
localparam integer SYMS = 140;          // QPSK symbols (280 bits of the frame ROM)
localparam integer CLK_PERIOD_NS = 10;

reg clk = 1'b0;
reg rst = 1'b1;
reg start = 1'b0;
reg [INDEX_W-1:0] start_offset_cfg = {INDEX_W{1'b0}};

wire busy;
wire done;
wire tx_valid;
wire signed [W-1:0] tx_i;
wire signed [W-1:0] tx_q;
wire timed_out;
wire [INDEX_W-1:0] received_symbols;
wire [INDEX_W-1:0] total_bit_errors;

integer so, w;
integer best_err = 32'h7fffffff;
integer best_so = -1;
integer best_rx = 0;
reg [INDEX_W-1:0] rxsyms;
reg [INDEX_W-1:0] errs;

qpsk_zynq_ber_top #(
    .W(W),
    .SPS(8),
    .INDEX_W(INDEX_W),
    .MAX_FRAME_BITS(512),
    .PHASE_W(3),
    .FLUSH_SYMBOLS(16)
) dut (
    .clk(clk),
    .rst(rst),
    .start(start),
    .symbol_count(SYMS[INDEX_W-1:0]),
    .start_offset(start_offset_cfg),
    .busy(busy),
    .done(done),
    .tx_valid(tx_valid),
    .tx_i(tx_i),
    .tx_q(tx_q),
    .rx_valid(tx_valid),        // ideal loopback: TX samples straight into RX
    .rx_i(tx_i),
    .rx_q(tx_q),
    .timed_out(timed_out),
    .received_symbols(received_symbols),
    .total_bit_errors(total_bit_errors),
    .debug_symbol_valid(),
    .debug_symbol_i(),
    .debug_symbol_q()
);

always #(CLK_PERIOD_NS/2) clk = ~clk;

initial begin
    $dumpfile("blocks/block_05_fpga_hdl_flow/tb/tb_qpsk_zynq_ber_top.vcd");
    $dumpvars(0, tb_qpsk_zynq_ber_top);

    repeat (5) @(posedge clk);
    @(negedge clk); rst = 1'b0;

    // Sweep a window around the known TX+RX matched-filter latency (~62) so the
    // test finds the aligning sampling phase and stays robust to small RTL changes.
    for (so = 48; so <= 76; so = so + 1) begin
        start_offset_cfg = so[INDEX_W-1:0];
        @(negedge clk); start = 1'b1;
        @(negedge clk); start = 1'b0;

        w = 0;
        while (!done && w < 8192) begin @(posedge clk); w = w + 1; end
        @(posedge clk);                 // let received/errors settle
        rxsyms = received_symbols;
        errs = total_bit_errors;
        if (rxsyms == SYMS[INDEX_W-1:0] && errs < best_err) begin
            best_err = errs; best_so = so; best_rx = rxsyms;
        end

        w = 0;
        while (busy && w < 8192) begin @(posedge clk); w = w + 1; end
        repeat (4) @(posedge clk);
    end

    $display("QPSK loopback sweep: best start_offset=%0d received=%0d/%0d symbols, bit_errors=%0d/%0d",
             best_so, best_rx, SYMS, best_err, 2*SYMS);
    if (best_so >= 0 && best_err == 0)
        $display("PASS: qpsk_zynq_ber_top loopback recovered %0d QPSK symbols at BER=0 (start_offset=%0d)",
                 SYMS, best_so);
    else begin
        $display("FAIL: no start_offset gave QPSK BER=0 (best bit_errors=%0d)", best_err);
        $fatal(1);
    end
    $finish;
end

endmodule
