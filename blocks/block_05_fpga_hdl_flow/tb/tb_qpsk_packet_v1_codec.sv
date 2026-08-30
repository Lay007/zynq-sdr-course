`timescale 1ns/1ps

module tb_qpsk_packet_v1_codec;

reg clk = 1'b0;
reg rst = 1'b1;

reg enc_s_valid = 1'b0;
wire enc_s_ready;
reg [7:0] enc_s_length = 8'd0;
reg [15:0] enc_s_sequence = 16'd0;
reg [215:0] enc_s_payload = 216'd0;
wire enc_m_valid;
reg enc_m_ready = 1'b0;
wire [255:0] enc_m_packet;

reg dec_s_valid = 1'b0;
wire dec_s_ready;
reg [255:0] dec_s_packet = 256'd0;
wire dec_m_valid;
reg dec_m_ready = 1'b0;
wire [7:0] dec_m_length;
wire [15:0] dec_m_sequence;
wire [215:0] dec_m_payload;
wire dec_m_crc_ok;
wire dec_m_frame_error;

reg [255:0] held_packet;
reg [215:0] hello_payload;
integer index;

localparam [255:0] HELLO_PACKET =
    256'h102b00000000000000000041206472616f62206d6f7266206f6c6c6548001112;
localparam [255:0] INVALID_LENGTH_PACKET =
    256'hd00000000000000000000000000000000000000000000000000000000000091c;

qpsk_packet_v1_encoder encoder_i (
    .clk(clk), .rst(rst),
    .s_valid(enc_s_valid), .s_ready(enc_s_ready),
    .s_length(enc_s_length), .s_sequence(enc_s_sequence), .s_payload(enc_s_payload),
    .m_valid(enc_m_valid), .m_ready(enc_m_ready), .m_packet(enc_m_packet)
);

qpsk_packet_v1_decoder decoder_i (
    .clk(clk), .rst(rst),
    .s_valid(dec_s_valid), .s_ready(dec_s_ready), .s_packet(dec_s_packet),
    .m_valid(dec_m_valid), .m_ready(dec_m_ready),
    .m_length(dec_m_length), .m_sequence(dec_m_sequence), .m_payload(dec_m_payload),
    .m_crc_ok(dec_m_crc_ok), .m_frame_error(dec_m_frame_error)
);

always #5 clk = ~clk;

task send_encoder;
    input [7:0] length;
    input [15:0] seq_value;
    input [215:0] payload_value;
    begin
        while (!enc_s_ready) @(posedge clk);
        @(negedge clk);
        enc_s_length = length;
        enc_s_sequence = seq_value;
        enc_s_payload = payload_value;
        enc_s_valid = 1'b1;
        @(negedge clk);
        enc_s_valid = 1'b0;
    end
endtask

task send_decoder;
    input [255:0] packet;
    begin
        while (!dec_s_ready) @(posedge clk);
        @(negedge clk);
        dec_s_packet = packet;
        dec_s_valid = 1'b1;
        @(negedge clk);
        dec_s_valid = 1'b0;
    end
endtask

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

    repeat (4) @(posedge clk);
    @(negedge clk); rst = 1'b0;
    if (enc_m_valid || dec_m_valid) begin
        $display("FAIL: valid asserted after reset");
        $fatal(1);
    end

    // Known packet and exact bus byte placement.
    send_encoder(8'd18, 16'd17, hello_payload);
    wait (enc_m_valid);
    held_packet = enc_m_packet;
    repeat (3) begin
        @(posedge clk);
        if (!enc_m_valid || enc_m_packet !== held_packet) begin
            $display("FAIL: encoder output changed under backpressure");
            $fatal(1);
        end
    end
    if (enc_m_packet !== HELLO_PACKET) begin
        $display("FAIL: packet mapping mismatch\n got=%064x\n exp=%064x",
                 enc_m_packet, HELLO_PACKET);
        $fatal(1);
    end
    $display("PASS: packet byte 0 maps to bus[7:0], byte 31 to bus[255:248]");
    @(negedge clk); enc_m_ready = 1'b1;
    @(negedge clk); enc_m_ready = 1'b0;

    // Decode the known packet and hold the result under backpressure.
    send_decoder(HELLO_PACKET);
    wait (dec_m_valid);
    repeat (2) @(posedge clk);
    if (!dec_m_valid || dec_m_length != 18 || dec_m_sequence != 17 ||
        dec_m_payload !== hello_payload || !dec_m_crc_ok || dec_m_frame_error) begin
        $display("FAIL: known packet did not decode exactly");
        $fatal(1);
    end
    $display("PASS: packet-v1 encode/decode and CRC result");
    @(negedge clk); dec_m_ready = 1'b1;
    @(negedge clk); dec_m_ready = 1'b0;

    // Payload and CRC corruption are both detected.
    send_decoder(HELLO_PACKET ^ (256'd1 << (8*7 + 5)));
    wait (dec_m_valid);
    if (dec_m_crc_ok || dec_m_frame_error) begin
        $display("FAIL: corrupted payload was accepted");
        $fatal(1);
    end
    @(negedge clk); dec_m_ready = 1'b1;
    @(negedge clk); dec_m_ready = 1'b0;

    send_decoder(HELLO_PACKET ^ (256'd1 << 248));
    wait (dec_m_valid);
    if (dec_m_crc_ok) begin
        $display("FAIL: corrupted CRC was accepted");
        $fatal(1);
    end
    $display("PASS: payload-bit and CRC-bit corruption detected");
    @(negedge clk); dec_m_ready = 1'b1;
    @(negedge clk); dec_m_ready = 1'b0;

    // A CRC-consistent packet can still fail the packet-v1 length contract.
    send_decoder(INVALID_LENGTH_PACKET);
    wait (dec_m_valid);
    if (!dec_m_crc_ok || !dec_m_frame_error || dec_m_length != 28) begin
        $display("FAIL: invalid length field was not reported");
        $fatal(1);
    end
    $display("PASS: invalid length field reported independently of CRC");

    // Synchronous reset clears a pending valid result.
    @(negedge clk); rst = 1'b1;
    @(posedge clk); #1;
    if (enc_m_valid || dec_m_valid) begin
        $display("FAIL: reset did not clear valid state");
        $fatal(1);
    end
    $display("PASS: reset and ready/valid semantics");
    $finish;
end

endmodule
