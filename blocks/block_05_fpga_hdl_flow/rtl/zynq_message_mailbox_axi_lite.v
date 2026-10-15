// Lab 5.12 - educational Zynq PS/PL AXI-Lite message mailbox.
//
// The first hardware exercise is deliberately a PL echo, not DMA and not RF:
//
//   PS writes TX registers -> TX_START -> PL copies TX to RX -> RX_VALID -> PS reads/acks.
//
// This keeps the complete PS/PL transaction visible to a learner.  A later lab
// replaces the echo operation with the existing QPSK modem while preserving the
// same software-visible register contract.
//
// Clock/reset contract:
//   * one AXI/PL clock domain only;
//   * s_axi_aresetn is sampled synchronously and is active low;
//   * RX payload/meta remain stable while RX_VALID=1 until RX_ACK;
//   * a new completed echo while RX_VALID=1 preserves the old RX snapshot and
//     sets RX_OVERFLOW.
//
// MODE = 1 (Lab 11.49, issue #55): the same registers, but TX_START sends the message through the
// QPSK modem of the gpreg bridge instead of echoing it. The core builds a packet-v1 frame from
// TX_SEQUENCE (low 16 bits), TX_LENGTH (at most 27 bytes) and TX_DATA (bytes little-endian in the
// words): length, sequence, payload, zero padding, CRC-16/CCITT-FALSE over bytes 0..29, LSB first,
// then PN9-whitened, exactly like zmsg and two_board_message.py. The bridge transmits it once and,
// on a single board with TX1 cabled to RX1, receives it; the core de-whitens the received bits,
// checks the CRC and fills the RX registers: RX_META.CRC_OK when the CRC matches and the length is
// valid, RX_META.FRAME_ERROR when no frame was received or the length is out of range. A TX_LENGTH
// over 27 is not sent and completes at once with FRAME_ERROR. The modem handshake crosses clock
// domains with toggles: modem_tx_bits is stable before modem_tx_toggle changes, and the bridge
// keeps modem_rx_bits stable after it changes modem_rx_toggle.

`timescale 1ns/1ps

module zynq_message_mailbox_axi_lite #(
    parameter integer AXI_ADDR_W = 8,
    parameter integer AXI_DATA_W = 32,
    parameter integer MODE = 0,                  // 0 = PL echo (Lab 5.12), 1 = QPSK modem (Lab 11.49)
    parameter integer MODEM_TIMEOUT = 50000000   // AXI clocks to wait for the modem (0.5 s at 100 MHz)
) (
    input  wire                         s_axi_aclk,
    input  wire                         s_axi_aresetn,

    input  wire [AXI_ADDR_W-1:0]        s_axi_awaddr,
    input  wire                         s_axi_awvalid,
    output reg                          s_axi_awready,

    input  wire [AXI_DATA_W-1:0]        s_axi_wdata,
    input  wire [(AXI_DATA_W/8)-1:0]    s_axi_wstrb,
    input  wire                         s_axi_wvalid,
    output reg                          s_axi_wready,

    output reg  [1:0]                   s_axi_bresp,
    output reg                          s_axi_bvalid,
    input  wire                         s_axi_bready,

    input  wire [AXI_ADDR_W-1:0]        s_axi_araddr,
    input  wire                         s_axi_arvalid,
    output reg                          s_axi_arready,

    output reg  [AXI_DATA_W-1:0]        s_axi_rdata,
    output reg  [1:0]                   s_axi_rresp,
    output reg                          s_axi_rvalid,
    input  wire                         s_axi_rready,

    // MODE = 1 only (leave unconnected in MODE = 0)
    output reg  [255:0]                 modem_tx_bits,
    output reg                          modem_tx_toggle,
    input  wire [255:0]                 modem_rx_bits,
    input  wire                         modem_rx_toggle,
    input  wire                         modem_rx_locked
);

localparam integer AXI_STRB_W = AXI_DATA_W / 8;
localparam integer MAILBOX_WORDS = 16;
localparam [31:0] CORE_ID = 32'h4D424F58;      // "MBOX"
localparam [31:0] CORE_VERSION = (MODE == 1) ? 32'h00020000 : 32'h00010000;
localparam integer MAX_PAYLOAD = 27;
// PN9 (x^9 + x^5 + 1, seed 0x1FF), bit i = the i-th output bit; the same sequence as zmsg.c.
localparam [255:0] PN9 = 256'h0ccac9fb4937e5a8513b2f61aa721884022323ab638951b3e78b72904ce8fbc1;

localparam [AXI_ADDR_W-1:0] REG_ID          = 8'h00;
localparam [AXI_ADDR_W-1:0] REG_VERSION     = 8'h04;
localparam [AXI_ADDR_W-1:0] REG_CONTROL     = 8'h08;
localparam [AXI_ADDR_W-1:0] REG_STATUS      = 8'h0C;
localparam [AXI_ADDR_W-1:0] REG_TX_SEQUENCE = 8'h10;
localparam [AXI_ADDR_W-1:0] REG_TX_LENGTH   = 8'h14;
localparam [AXI_ADDR_W-1:0] REG_TX_DATA0    = 8'h20;
localparam [AXI_ADDR_W-1:0] REG_RX_SEQUENCE = 8'h60;
localparam [AXI_ADDR_W-1:0] REG_RX_LENGTH   = 8'h64;
localparam [AXI_ADDR_W-1:0] REG_RX_META     = 8'h68;
localparam [AXI_ADDR_W-1:0] REG_RX_DATA0    = 8'h70;

localparam [31:0] CONTROL_TX_START = 32'h00000001;
localparam [31:0] CONTROL_RX_ACK   = 32'h00000002;

localparam [31:0] RX_META_CRC_OK      = 32'h00000001;
localparam [31:0] RX_META_FRAME_ERROR = 32'h00000002;

reg [31:0] tx_sequence;
reg [31:0] tx_length;
reg [31:0] tx_data [0:MAILBOX_WORDS-1];

reg [31:0] rx_sequence;
reg [31:0] rx_length;
reg [31:0] rx_meta;
reg [31:0] rx_data [0:MAILBOX_WORDS-1];

reg tx_busy;
reg tx_done;
reg modem_wait;
reg [31:0] modem_timer;
reg [2:0] modem_rx_sync;
reg rx_valid;
reg rx_overflow;
reg echo_pending;

reg [AXI_ADDR_W-1:0] awaddr_latched;
reg awaddr_valid;
reg [AXI_DATA_W-1:0] wdata_latched;
reg [AXI_STRB_W-1:0] wstrb_latched;
reg wdata_valid;

reg [AXI_DATA_W-1:0] read_word;
reg [AXI_DATA_W-1:0] write_word;
integer idx;
integer read_idx;
integer write_idx;

function [AXI_DATA_W-1:0] apply_wstrb;
    input [AXI_DATA_W-1:0] current_value;
    input [AXI_DATA_W-1:0] new_value;
    input [AXI_STRB_W-1:0] strobe;
    integer byte_idx;
    begin
        apply_wstrb = current_value;
        for (byte_idx = 0; byte_idx < AXI_STRB_W; byte_idx = byte_idx + 1) begin
            if (strobe[byte_idx]) begin
                apply_wstrb[byte_idx*8 +: 8] = new_value[byte_idx*8 +: 8];
            end
        end
    end
endfunction

// --- MODE = 1: packet-v1 framing ---------------------------------------------------------------
function [15:0] crc16_ccitt_false;    // over bytes 0..29 of a packet held LSB-first in pkt[239:0]
    input [239:0] pkt;
    integer b, i;
    reg [15:0] c;
    begin
        c = 16'hFFFF;
        for (b = 0; b < 30; b = b + 1) begin
            c = c ^ {pkt[8*b +: 8], 8'h00};
            for (i = 0; i < 8; i = i + 1)
                c = c[15] ? ((c << 1) ^ 16'h1021) : (c << 1);
        end
        crc16_ccitt_false = c;
    end
endfunction

reg [255:0] tx_packet;                // packet-v1 built from the TX registers, before whitening
integer pb;
always @(*) begin
    tx_packet = 256'd0;
    tx_packet[7:0] = tx_length[7:0];
    tx_packet[15:8] = tx_sequence[7:0];
    tx_packet[23:16] = tx_sequence[15:8];
    for (pb = 0; pb < MAX_PAYLOAD; pb = pb + 1)
        if (pb < tx_length)
            tx_packet[8*(3 + pb) +: 8] = tx_data[pb / 4][8*(pb % 4) +: 8];
    tx_packet[255:240] = crc16_ccitt_false(tx_packet[239:0]);
end

wire [255:0] rx_packet = modem_rx_bits ^ PN9;
wire [15:0]  rx_crc = crc16_ccitt_false(rx_packet[239:0]);
wire         rx_crc_ok = (rx_crc == rx_packet[255:240]);
wire [7:0]   rx_len = rx_packet[7:0];
wire         rx_toggle_edge = modem_rx_sync[2] ^ modem_rx_sync[1];
reg  [223:0] rx_payload;            // the received payload bytes, zero beyond RX length
always @(*) begin
    rx_payload = 224'd0;
    for (pb = 0; pb < MAX_PAYLOAD; pb = pb + 1)
        if (pb < rx_len)
            rx_payload[8*pb +: 8] = rx_packet[8*(3 + pb) +: 8];
end

always @(*) begin
    read_word = {AXI_DATA_W{1'b0}};
    read_idx = 0;

    case (s_axi_araddr)
        REG_ID:          read_word = CORE_ID;
        REG_VERSION:     read_word = CORE_VERSION;
        REG_CONTROL:     read_word = {AXI_DATA_W{1'b0}};
        REG_STATUS:      read_word = {28'd0, rx_overflow, rx_valid, tx_done, tx_busy};
        REG_TX_SEQUENCE: read_word = tx_sequence;
        REG_TX_LENGTH:   read_word = tx_length;
        REG_RX_SEQUENCE: read_word = rx_sequence;
        REG_RX_LENGTH:   read_word = rx_length;
        REG_RX_META:     read_word = rx_meta;
        default: begin
            if ((s_axi_araddr >= REG_TX_DATA0) &&
                (s_axi_araddr < REG_TX_DATA0 + MAILBOX_WORDS*4) &&
                (s_axi_araddr[1:0] == 2'b00)) begin
                read_idx = (s_axi_araddr - REG_TX_DATA0) >> 2;
                read_word = tx_data[read_idx];
            end else if ((s_axi_araddr >= REG_RX_DATA0) &&
                         (s_axi_araddr < REG_RX_DATA0 + MAILBOX_WORDS*4) &&
                         (s_axi_araddr[1:0] == 2'b00)) begin
                read_idx = (s_axi_araddr - REG_RX_DATA0) >> 2;
                read_word = rx_data[read_idx];
            end
        end
    endcase
end

always @(posedge s_axi_aclk) begin
    if (!s_axi_aresetn) begin
        s_axi_awready <= 1'b0;
        s_axi_wready <= 1'b0;
        s_axi_bresp <= 2'b00;
        s_axi_bvalid <= 1'b0;
        s_axi_arready <= 1'b0;
        s_axi_rdata <= {AXI_DATA_W{1'b0}};
        s_axi_rresp <= 2'b00;
        s_axi_rvalid <= 1'b0;

        awaddr_latched <= {AXI_ADDR_W{1'b0}};
        awaddr_valid <= 1'b0;
        wdata_latched <= {AXI_DATA_W{1'b0}};
        wstrb_latched <= {AXI_STRB_W{1'b0}};
        wdata_valid <= 1'b0;

        tx_sequence <= 32'd0;
        tx_length <= 32'd0;
        rx_sequence <= 32'd0;
        rx_length <= 32'd0;
        rx_meta <= 32'd0;
        tx_busy <= 1'b0;
        tx_done <= 1'b0;
        rx_valid <= 1'b0;
        rx_overflow <= 1'b0;
        echo_pending <= 1'b0;
        modem_wait <= 1'b0;
        modem_timer <= 32'd0;
        modem_rx_sync <= 3'd0;
        modem_tx_bits <= 256'd0;
        modem_tx_toggle <= 1'b0;

        for (idx = 0; idx < MAILBOX_WORDS; idx = idx + 1) begin
            tx_data[idx] <= 32'd0;
            rx_data[idx] <= 32'd0;
        end
    end else begin
        // The tiny educational echo takes one PL clock after TX_START.  This
        // makes TX_BUSY a real state instead of a purely combinational event.
        if (echo_pending) begin
            echo_pending <= 1'b0;
            tx_busy <= 1'b0;
            tx_done <= 1'b1;

            if (rx_valid) begin
                // Preserve the unread message.  Software must acknowledge it.
                rx_overflow <= 1'b1;
            end else begin
                rx_sequence <= tx_sequence;
                if (tx_length <= 32'd64) begin
                    rx_length <= tx_length;
                    rx_meta <= RX_META_CRC_OK;
                end else begin
                    rx_length <= 32'd64;
                    rx_meta <= RX_META_FRAME_ERROR;
                end
                for (idx = 0; idx < MAILBOX_WORDS; idx = idx + 1) begin
                    rx_data[idx] <= tx_data[idx];
                end
                rx_valid <= 1'b1;
            end
        end

        // MODE = 1: wait for the modem's answer (or give up), then fill RX like the echo does.
        modem_rx_sync <= {modem_rx_sync[1:0], (MODE == 1) ? modem_rx_toggle : 1'b0};
        if (MODE == 1 && modem_wait) begin
            modem_timer <= modem_timer + 1'b1;
            if (rx_toggle_edge || modem_timer == MODEM_TIMEOUT) begin
                modem_wait <= 1'b0;
                tx_busy <= 1'b0;
                tx_done <= 1'b1;
                if (rx_valid) begin
                    rx_overflow <= 1'b1;
                end else begin
                    rx_valid <= 1'b1;
                    for (idx = 0; idx < MAILBOX_WORDS; idx = idx + 1)
                        rx_data[idx] <= 32'd0;
                    if (rx_toggle_edge && modem_rx_locked) begin
                        rx_sequence <= {16'd0, rx_packet[23:8]};
                        rx_length <= (rx_len <= MAX_PAYLOAD) ? {24'd0, rx_len} : 32'd0;
                        rx_meta <= (rx_len > MAX_PAYLOAD) ? RX_META_FRAME_ERROR
                                 : (rx_crc_ok ? RX_META_CRC_OK : 32'd0);
                        for (idx = 0; idx < 7; idx = idx + 1)     // 27 payload bytes = 7 words
                            rx_data[idx] <= rx_payload[32*idx +: 32];
                    end else begin
                        rx_sequence <= 32'd0;
                        rx_length <= 32'd0;
                        rx_meta <= RX_META_FRAME_ERROR;           // no frame received
                    end
                end
            end
        end

        s_axi_awready <= (!awaddr_valid) && (!s_axi_bvalid);
        s_axi_wready <= (!wdata_valid) && (!s_axi_bvalid);
        s_axi_arready <= (!s_axi_rvalid);

        if (s_axi_awready && s_axi_awvalid) begin
            awaddr_latched <= s_axi_awaddr;
            awaddr_valid <= 1'b1;
        end

        if (s_axi_wready && s_axi_wvalid) begin
            wdata_latched <= s_axi_wdata;
            wstrb_latched <= s_axi_wstrb;
            wdata_valid <= 1'b1;
        end

        if (awaddr_valid && wdata_valid && !s_axi_bvalid) begin
            write_word = {AXI_DATA_W{1'b0}};
            write_idx = 0;

            case (awaddr_latched)
                REG_CONTROL: begin
                    if (wstrb_latched[0] &&
                        (wdata_latched & CONTROL_RX_ACK) != 0) begin
                        rx_valid <= 1'b0;
                        rx_overflow <= 1'b0;
                    end

                    if (wstrb_latched[0] &&
                        (wdata_latched & CONTROL_TX_START) != 0 &&
                        !tx_busy) begin
                        tx_busy <= 1'b1;
                        tx_done <= 1'b0;
                        if (MODE == 0) begin
                            echo_pending <= 1'b1;
                        end else if (tx_length > MAX_PAYLOAD) begin
                            // Not sendable: complete at once (next cycle) with FRAME_ERROR.
                            modem_wait <= 1'b1;
                            modem_timer <= MODEM_TIMEOUT;
                        end else begin
                            modem_tx_bits <= tx_packet ^ PN9;
                            modem_tx_toggle <= ~modem_tx_toggle;
                            modem_wait <= 1'b1;
                            modem_timer <= 32'd0;
                        end
                    end
                end

                REG_TX_SEQUENCE: begin
                    tx_sequence <= apply_wstrb(
                        tx_sequence, wdata_latched, wstrb_latched
                    );
                end

                REG_TX_LENGTH: begin
                    tx_length <= apply_wstrb(
                        tx_length, wdata_latched, wstrb_latched
                    );
                end

                default: begin
                    if ((awaddr_latched >= REG_TX_DATA0) &&
                        (awaddr_latched < REG_TX_DATA0 + MAILBOX_WORDS*4) &&
                        (awaddr_latched[1:0] == 2'b00)) begin
                        write_idx = (awaddr_latched - REG_TX_DATA0) >> 2;
                        write_word = apply_wstrb(
                            tx_data[write_idx], wdata_latched, wstrb_latched
                        );
                        tx_data[write_idx] <= write_word;
                    end
                end
            endcase

            awaddr_valid <= 1'b0;
            wdata_valid <= 1'b0;
            s_axi_bvalid <= 1'b1;
            s_axi_bresp <= 2'b00;
        end

        if (s_axi_bvalid && s_axi_bready) begin
            s_axi_bvalid <= 1'b0;
        end

        if (s_axi_arready && s_axi_arvalid) begin
            s_axi_rdata <= read_word;
            s_axi_rresp <= 2'b00;
            s_axi_rvalid <= 1'b1;
        end

        if (s_axi_rvalid && s_axi_rready) begin
            s_axi_rvalid <= 1'b0;
        end
    end
end

endmodule
