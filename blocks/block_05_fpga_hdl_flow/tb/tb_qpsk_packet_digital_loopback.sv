`timescale 1ns/1ps

module tb_qpsk_packet_digital_loopback;

reg clk = 1'b0;
reg rst = 1'b1;
reg start = 1'b0;
reg [7:0] tx_length = 8'd0;
reg [15:0] tx_sequence = 16'd0;
reg [215:0] tx_payload = 216'd0;
wire busy;
wire done;
wire rx_valid;
wire [7:0] rx_length;
wire [15:0] rx_sequence;
wire [215:0] rx_payload;
wire rx_crc_ok;
wire rx_frame_error;

reg [215:0] hello_payload;
integer wait_cycles;

qpsk_packet_digital_loopback dut (
    .clk(clk), .rst(rst), .start(start),
    .tx_length(tx_length), .tx_sequence(tx_sequence), .tx_payload(tx_payload),
    .busy(busy), .done(done), .rx_valid(rx_valid),
    .rx_length(rx_length), .rx_sequence(rx_sequence), .rx_payload(rx_payload),
    .rx_crc_ok(rx_crc_ok), .rx_frame_error(rx_frame_error)
);

always #4 clk = ~clk;

initial begin
    hello_payload = 216'd0;
    hello_payload[8*0 +: 8] = "H";
    hello_payload[8*1 +: 8] = "e";
    hello_payload[8*2 +: 8] = "l";
    hello_payload[8*3 +: 8] = "l";
    hello_payload[8*4 +: 8] = "o";
    hello_payload[8*5 +: 8] = " ";
    hello_payload[8*6 +: 8] = "f";
    hello_payload[8*7 +: 8] = "r";
    hello_payload[8*8 +: 8] = "o";
    hello_payload[8*9 +: 8] = "m";
    hello_payload[8*10 +: 8] = " ";
    hello_payload[8*11 +: 8] = "b";
    hello_payload[8*12 +: 8] = "o";
    hello_payload[8*13 +: 8] = "a";
    hello_payload[8*14 +: 8] = "r";
    hello_payload[8*15 +: 8] = "d";
    hello_payload[8*16 +: 8] = " ";
    hello_payload[8*17 +: 8] = "A";

    repeat (8) @(posedge clk);
    @(negedge clk); rst = 1'b0;
    repeat (4) @(posedge clk);

    tx_length = 8'd18;
    tx_sequence = 16'd17;
    tx_payload = hello_payload;
    @(negedge clk); start = 1'b1;
    @(negedge clk); start = 1'b0;

    wait_cycles = 0;
    while (!done && wait_cycles < 30000) begin
        @(posedge clk);
        wait_cycles = wait_cycles + 1;
    end

    if (!done || !rx_valid) begin
        $display("FAIL: packet loopback timed out after %0d clocks", wait_cycles);
        $fatal(1);
    end
    if (rx_length != 18 || rx_sequence != 17 || rx_payload !== hello_payload) begin
        $display("FAIL: mailbox fields changed length=%0d sequence=%0d", rx_length, rx_sequence);
        $fatal(1);
    end
    if (!rx_crc_ok || rx_frame_error) begin
        $display("FAIL: recovered packet integrity crc_ok=%0d frame_error=%0d",
                 rx_crc_ok, rx_frame_error);
        $fatal(1);
    end
    if (busy) begin
        $display("FAIL: busy remained asserted after decoded result");
        $fatal(1);
    end

    $display("PASS: packet digital loopback payload=\"Hello from board A\" sequence=17 CRC=OK");

    @(negedge clk); rst = 1'b1;
    @(posedge clk); #1;
    if (busy || done || rx_valid) begin
        $display("FAIL: reset did not clear loopback state");
        $fatal(1);
    end
    $display("PASS: packet digital loopback reset semantics");
    $finish;
end

endmodule
