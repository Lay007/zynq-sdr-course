// Packet-v1 codec for the existing 256-bit QPSK application payload.
//
// Numerical contract:
//   packet byte n -> m_packet[8*n +: 8]
//   sequence and CRC fields are little-endian
//   CRC-16/CCITT-FALSE covers bytes 0..29
//     poly=0x1021 init=0xffff refin=0 refout=0 xorout=0
//
// Both directions use a one-entry ready/valid register. Outputs remain stable
// while m_valid=1 and m_ready=0. Reset is synchronous, active high.

`timescale 1ns/1ps

module qpsk_packet_v1_encoder (
    input  wire           clk,
    input  wire           rst,
    input  wire           s_valid,
    output wire           s_ready,
    input  wire [7:0]     s_length,
    input  wire [15:0]    s_sequence,
    input  wire [215:0]   s_payload,
    output reg            m_valid,
    input  wire           m_ready,
    output reg [255:0]    m_packet
);

integer byte_index;
reg [255:0] packet_work;
reg [15:0] crc_work;

function [15:0] crc16_ccitt_false;
    input [239:0] data;
    integer data_index;
    integer bit_index;
    reg [15:0] crc;
    reg [7:0] data_byte;
    begin
        crc = 16'hffff;
        for (data_index = 0; data_index < 30; data_index = data_index + 1) begin
            data_byte = data[data_index*8 +: 8];
            crc = crc ^ {data_byte, 8'h00};
            for (bit_index = 0; bit_index < 8; bit_index = bit_index + 1) begin
                if (crc[15]) crc = (crc << 1) ^ 16'h1021;
                else crc = crc << 1;
            end
        end
        crc16_ccitt_false = crc;
    end
endfunction

assign s_ready = ~m_valid || m_ready;

always @(posedge clk) begin
    if (rst) begin
        m_valid <= 1'b0;
        m_packet <= 256'd0;
    end else if (s_ready) begin
        m_valid <= s_valid;
        if (s_valid) begin
            packet_work = 256'd0;
            packet_work[7:0] = s_length;
            packet_work[15:8] = s_sequence[7:0];
            packet_work[23:16] = s_sequence[15:8];
            for (byte_index = 0; byte_index < 27; byte_index = byte_index + 1)
                packet_work[(byte_index+3)*8 +: 8] =
                    (byte_index < s_length) ? s_payload[byte_index*8 +: 8] : 8'h00;
            crc_work = crc16_ccitt_false(packet_work[239:0]);
            packet_work[247:240] = crc_work[7:0];
            packet_work[255:248] = crc_work[15:8];
            m_packet <= packet_work;
        end
    end
end

endmodule


module qpsk_packet_v1_decoder (
    input  wire           clk,
    input  wire           rst,
    input  wire           s_valid,
    output wire           s_ready,
    input  wire [255:0]   s_packet,
    output reg            m_valid,
    input  wire           m_ready,
    output reg [7:0]      m_length,
    output reg [15:0]     m_sequence,
    output reg [215:0]    m_payload,
    output reg            m_crc_ok,
    output reg            m_frame_error
);

integer byte_index;
reg [15:0] crc_work;

function [15:0] crc16_ccitt_false;
    input [239:0] data;
    integer data_index;
    integer bit_index;
    reg [15:0] crc;
    reg [7:0] data_byte;
    begin
        crc = 16'hffff;
        for (data_index = 0; data_index < 30; data_index = data_index + 1) begin
            data_byte = data[data_index*8 +: 8];
            crc = crc ^ {data_byte, 8'h00};
            for (bit_index = 0; bit_index < 8; bit_index = bit_index + 1) begin
                if (crc[15]) crc = (crc << 1) ^ 16'h1021;
                else crc = crc << 1;
            end
        end
        crc16_ccitt_false = crc;
    end
endfunction

assign s_ready = ~m_valid || m_ready;

always @(posedge clk) begin
    if (rst) begin
        m_valid <= 1'b0;
        m_length <= 8'd0;
        m_sequence <= 16'd0;
        m_payload <= 216'd0;
        m_crc_ok <= 1'b0;
        m_frame_error <= 1'b0;
    end else if (s_ready) begin
        m_valid <= s_valid;
        if (s_valid) begin
            m_length <= s_packet[7:0];
            m_sequence <= {s_packet[23:16], s_packet[15:8]};
            for (byte_index = 0; byte_index < 27; byte_index = byte_index + 1)
                m_payload[byte_index*8 +: 8] <= s_packet[(byte_index+3)*8 +: 8];
            crc_work = crc16_ccitt_false(s_packet[239:0]);
            m_crc_ok <= crc_work == {s_packet[255:248], s_packet[247:240]};
            m_frame_error <= s_packet[7:0] > 8'd27;
        end
    end
end

endmodule
