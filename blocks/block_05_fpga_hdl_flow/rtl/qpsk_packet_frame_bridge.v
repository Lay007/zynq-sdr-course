// Mailbox-facing packet frame adapters for the existing course QPSK modem.
//
// TX prepends the unchanged 24-bit course preamble to one 256-bit packet.
// RX collects the normalized post-frame-sync payload bits exposed by the
// existing QPSK BER/frame-sync block. Packet byte n occupies bits 8*n +: 8;
// bit 0 of each byte is carried first.

`timescale 1ns/1ps

module qpsk_packet_frame_source #(
    parameter integer INDEX_W = 16,
    parameter integer MAX_FRAME_BITS = 512,
    parameter integer PREAMBLE_BITS = 24,
    parameter MEM_FILE = "blocks/block_05_fpga_hdl_flow/rtl/bpsk_frame_bits.mem"
) (
    input  wire                    clk,
    input  wire                    rst,
    input  wire                    start,
    input  wire [255:0]            packet,
    input  wire                    out_ready,
    output wire                    out_valid,
    output wire [1:0]              out_dibit,
    output wire                    out_last,
    output reg                     busy,
    output reg                     done
);

localparam integer PREAMBLE_SYMBOLS = PREAMBLE_BITS / 2;
localparam integer PAYLOAD_SYMBOLS = 128;
localparam integer FRAME_SYMBOLS = PREAMBLE_SYMBOLS + PAYLOAD_SYMBOLS;

reg [0:0] frame_bits [0:MAX_FRAME_BITS-1];
reg [255:0] packet_reg = 256'd0;
reg [INDEX_W-1:0] symbol_index = {INDEX_W{1'b0}};
wire [INDEX_W-1:0] payload_symbol_index = symbol_index - PREAMBLE_SYMBOLS;
integer init_index;

assign out_valid = busy;
assign out_dibit = (symbol_index < PREAMBLE_SYMBOLS) ?
    {frame_bits[{symbol_index, 1'b1}], frame_bits[{symbol_index, 1'b0}]} :
    {packet_reg[{payload_symbol_index, 1'b1}],
     packet_reg[{payload_symbol_index, 1'b0}]};
assign out_last = busy && (symbol_index == FRAME_SYMBOLS - 1);

initial begin
    for (init_index = 0; init_index < MAX_FRAME_BITS; init_index = init_index + 1)
        frame_bits[init_index] = 1'b0;
    $readmemh(MEM_FILE, frame_bits);
end

always @(posedge clk) begin
    if (rst) begin
        packet_reg <= 256'd0;
        symbol_index <= {INDEX_W{1'b0}};
        busy <= 1'b0;
        done <= 1'b0;
    end else begin
        done <= 1'b0;
        if (start && !busy) begin
            packet_reg <= packet;
            symbol_index <= {INDEX_W{1'b0}};
            busy <= 1'b1;
        end else if (busy && out_ready) begin
            if (symbol_index == FRAME_SYMBOLS - 1) begin
                symbol_index <= {INDEX_W{1'b0}};
                busy <= 1'b0;
                done <= 1'b1;
            end else begin
                symbol_index <= symbol_index + 1'b1;
            end
        end
    end
end

endmodule


module qpsk_packet_payload_collector (
    input  wire           clk,
    input  wire           rst,
    input  wire           start,
    input  wire           in_valid,
    input  wire           in_bit,
    output reg            m_valid,
    input  wire           m_ready,
    output reg [255:0]    m_packet
);

reg [8:0] bit_index = 9'd0;

always @(posedge clk) begin
    if (rst || start) begin
        bit_index <= 9'd0;
        m_valid <= 1'b0;
        m_packet <= 256'd0;
    end else begin
        if (m_valid && m_ready) m_valid <= 1'b0;
        if (in_valid && !m_valid) begin
            m_packet[bit_index] <= in_bit;
            if (bit_index == 9'd255) begin
                bit_index <= 9'd0;
                m_valid <= 1'b1;
            end else begin
                bit_index <= bit_index + 1'b1;
            end
        end
    end
end

endmodule
