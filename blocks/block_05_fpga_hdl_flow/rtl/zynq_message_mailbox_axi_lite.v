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

`timescale 1ns/1ps

module zynq_message_mailbox_axi_lite #(
    parameter integer AXI_ADDR_W = 8,
    parameter integer AXI_DATA_W = 32
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
    input  wire                         s_axi_rready
);

localparam integer AXI_STRB_W = AXI_DATA_W / 8;
localparam integer MAILBOX_WORDS = 16;
localparam [31:0] CORE_ID = 32'h4D424F58;      // "MBOX"
localparam [31:0] CORE_VERSION = 32'h00010000;

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
                        echo_pending <= 1'b1;
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
