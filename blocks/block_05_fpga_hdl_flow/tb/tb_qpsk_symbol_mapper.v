// Lab 5.6b - self-checking testbench for qpsk_symbol_mapper
//
// Drives all four Gray-coded dibits and checks the registered I/Q symbol one
// cycle later, plus the Gray property (flipping one input bit flips exactly one
// axis) and that out_valid follows in_valid.

`timescale 1ns/1ps

module tb_qpsk_symbol_mapper;

localparam integer W = 16;
localparam signed [W-1:0] A = 16'sd23170;   // 32767 / sqrt(2)
localparam integer CLK = 10;

reg clk = 1'b0;
reg rst = 1'b1;
reg in_valid = 1'b0;
reg [1:0] in_dibit = 2'b00;

wire out_valid;
wire signed [W-1:0] out_i;
wire signed [W-1:0] out_q;

integer errors = 0;

qpsk_symbol_mapper #(.W(W)) dut (
    .clk(clk), .rst(rst),
    .in_valid(in_valid), .in_dibit(in_dibit),
    .out_valid(out_valid), .out_i(out_i), .out_q(out_q)
);

always #(CLK/2) clk = ~clk;

// Drive one dibit and check the symbol that appears one clock later.
task drive_check;
    input [1:0] db;
    input signed [W-1:0] ei;
    input signed [W-1:0] eq;
    begin
        @(negedge clk);
        in_valid = 1'b1;
        in_dibit = db;
        @(posedge clk); #1;
        if (out_valid !== 1'b1) begin
            $display("ERROR: dibit %b -> out_valid=%b (expected 1)", db, out_valid);
            errors = errors + 1;
        end
        if (out_i !== ei || out_q !== eq) begin
            $display("ERROR: dibit %b -> (%0d,%0d) expected (%0d,%0d)",
                     db, out_i, out_q, ei, eq);
            errors = errors + 1;
        end
    end
endtask

initial begin
    $dumpfile("blocks/block_05_fpga_hdl_flow/tb/tb_qpsk_symbol_mapper.vcd");
    $dumpvars(0, tb_qpsk_symbol_mapper);

    repeat (3) @(posedge clk);
    @(negedge clk); rst = 1'b0;

    // Gray QPSK: in_dibit[0] -> I, in_dibit[1] -> Q; bit=0 -> +A, bit=1 -> -A.
    drive_check(2'b00,  A,  A);   // (+A,+A)
    drive_check(2'b01, -A,  A);   // flip bit0 -> only I flips (Gray)
    drive_check(2'b11, -A, -A);   // flip bit1 -> only Q flips (Gray)
    drive_check(2'b10,  A, -A);   // flip bit0 -> only I flips (Gray)

    // idle: out_valid must drop the cycle after in_valid deasserts
    @(negedge clk); in_valid = 1'b0; in_dibit = 2'b00;
    @(posedge clk); #1;
    if (out_valid !== 1'b0) begin
        $display("ERROR: out_valid=%b after in_valid low (expected 0)", out_valid);
        errors = errors + 1;
    end

    repeat (2) @(posedge clk);
    if (errors == 0)
        $display("PASS: qpsk_symbol_mapper test completed without errors (4 Gray dibits)");
    else
        $display("FAIL: qpsk_symbol_mapper test completed with %0d errors", errors);
    if (errors != 0) $fatal(1);
    $finish;
end

endmodule
