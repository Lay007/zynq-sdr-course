// Lab 5.11 - AXI-Lite control wrapper for the deterministic BPSK BER top-level
//
// Exposes the framed BPSK start/config/result registers to a Zynq PS style
// control plane while keeping the sample-domain TX/RX seam explicit.

`timescale 1ns/1ps

module bpsk_zynq_ber_axi_lite #(
    parameter integer W = 16,
    parameter integer SPS = 8,
    parameter integer INDEX_W = 16,
    parameter integer MAX_FRAME_BITS = 512,
    parameter integer PHASE_W = 3,
    parameter integer FLUSH_SYMBOLS = 16,
    parameter integer AXI_ADDR_W = 6,
    parameter integer AXI_DATA_W = 32,
    parameter MEM_FILE = "blocks/block_05_fpga_hdl_flow/rtl/bpsk_frame_bits.mem"
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
    output wire                         tx_valid,
    output wire signed [W-1:0]          tx_i,
    output wire signed [W-1:0]          tx_q,
    input  wire                         rx_valid,
    input  wire signed [W-1:0]          rx_i,
    input  wire signed [W-1:0]          rx_q
);

localparam integer AXI_STRB_W = AXI_DATA_W / 8;
localparam [AXI_ADDR_W-1:0] REG_CONTROL_STATUS = 6'h00;
localparam [AXI_ADDR_W-1:0] REG_FRAME_BIT_COUNT = 6'h04;
localparam [AXI_ADDR_W-1:0] REG_PREAMBLE_COUNT = 6'h08;
localparam [AXI_ADDR_W-1:0] REG_START_OFFSET = 6'h0C;
localparam [AXI_ADDR_W-1:0] REG_RECEIVED_BITS = 6'h10;
localparam [AXI_ADDR_W-1:0] REG_TOTAL_ERRORS = 6'h14;
localparam [AXI_ADDR_W-1:0] REG_PAYLOAD_ERRORS = 6'h18;
localparam [AXI_ADDR_W-1:0] REG_ID = 6'h1C;
localparam [AXI_DATA_W-1:0] CORE_ID = 32'h4250534B; // "BPSK"

wire internal_rst = ~s_axi_aresetn;
wire core_busy;
wire core_done;
wire [INDEX_W-1:0] received_bits;
wire [INDEX_W-1:0] total_errors;
wire [INDEX_W-1:0] payload_errors;

reg [INDEX_W-1:0] frame_bit_count_reg = {INDEX_W{1'b0}};
reg [INDEX_W-1:0] preamble_count_reg = {INDEX_W{1'b0}};
reg [INDEX_W-1:0] start_offset_reg = {INDEX_W{1'b0}};
reg done_sticky = 1'b0;
reg start_pulse = 1'b0;

reg [AXI_ADDR_W-1:0] awaddr_latched = {AXI_ADDR_W{1'b0}};
reg awaddr_valid = 1'b0;
reg [AXI_DATA_W-1:0] wdata_latched = {AXI_DATA_W{1'b0}};
reg [AXI_STRB_W-1:0] wstrb_latched = {AXI_STRB_W{1'b0}};
reg wdata_valid = 1'b0;

integer byte_idx;
reg [AXI_DATA_W-1:0] write_word;
reg [AXI_DATA_W-1:0] read_word;

function [AXI_DATA_W-1:0] apply_wstrb;
    input [AXI_DATA_W-1:0] current_value;
    input [AXI_DATA_W-1:0] new_value;
    input [AXI_STRB_W-1:0] strobe;
    integer idx;
    begin
        apply_wstrb = current_value;
        for (idx = 0; idx < AXI_STRB_W; idx = idx + 1) begin
            if (strobe[idx]) begin
                apply_wstrb[idx*8 +: 8] = new_value[idx*8 +: 8];
            end
        end
    end
endfunction

bpsk_zynq_ber_top #(
    .W(W),
    .SPS(SPS),
    .INDEX_W(INDEX_W),
    .MAX_FRAME_BITS(MAX_FRAME_BITS),
    .PHASE_W(PHASE_W),
    .FLUSH_SYMBOLS(FLUSH_SYMBOLS),
    .MEM_FILE(MEM_FILE)
) core_i (
    .clk(s_axi_aclk),
    .rst(internal_rst),
    .start(start_pulse),
    .frame_bit_count(frame_bit_count_reg),
    .preamble_count(preamble_count_reg),
    .start_offset(start_offset_reg),
    .busy(core_busy),
    .done(core_done),
    .tx_valid(tx_valid),
    .tx_i(tx_i),
    .tx_q(tx_q),
    .rx_valid(rx_valid),
    .rx_i(rx_i),
    .rx_q(rx_q),
    .received_bits(received_bits),
    .total_errors(total_errors),
    .payload_errors(payload_errors)
);

always @(*) begin
    case (s_axi_araddr)
        REG_CONTROL_STATUS: read_word = {29'd0, done_sticky, core_busy, 1'b0};
        REG_FRAME_BIT_COUNT: read_word = {{(AXI_DATA_W-INDEX_W){1'b0}}, frame_bit_count_reg};
        REG_PREAMBLE_COUNT: read_word = {{(AXI_DATA_W-INDEX_W){1'b0}}, preamble_count_reg};
        REG_START_OFFSET: read_word = {{(AXI_DATA_W-INDEX_W){1'b0}}, start_offset_reg};
        REG_RECEIVED_BITS: read_word = {{(AXI_DATA_W-INDEX_W){1'b0}}, received_bits};
        REG_TOTAL_ERRORS: read_word = {{(AXI_DATA_W-INDEX_W){1'b0}}, total_errors};
        REG_PAYLOAD_ERRORS: read_word = {{(AXI_DATA_W-INDEX_W){1'b0}}, payload_errors};
        REG_ID: read_word = CORE_ID;
        default: read_word = {AXI_DATA_W{1'b0}};
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
        frame_bit_count_reg <= {INDEX_W{1'b0}};
        preamble_count_reg <= {INDEX_W{1'b0}};
        start_offset_reg <= {INDEX_W{1'b0}};
        done_sticky <= 1'b0;
        start_pulse <= 1'b0;
        awaddr_latched <= {AXI_ADDR_W{1'b0}};
        awaddr_valid <= 1'b0;
        wdata_latched <= {AXI_DATA_W{1'b0}};
        wstrb_latched <= {AXI_STRB_W{1'b0}};
        wdata_valid <= 1'b0;
    end else begin
        start_pulse <= 1'b0;

        if (core_done) begin
            done_sticky <= 1'b1;
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
            case (awaddr_latched)
                REG_CONTROL_STATUS: begin
                    if (wstrb_latched[0] && wdata_latched[0]) begin
                        start_pulse <= 1'b1;
                        done_sticky <= 1'b0;
                    end
                    if (wstrb_latched[0] && wdata_latched[2]) begin
                        done_sticky <= 1'b0;
                    end
                end
                REG_FRAME_BIT_COUNT: begin
                    write_word = apply_wstrb(
                        {{(AXI_DATA_W-INDEX_W){1'b0}}, frame_bit_count_reg},
                        wdata_latched,
                        wstrb_latched
                    );
                    frame_bit_count_reg <= write_word[INDEX_W-1:0];
                end
                REG_PREAMBLE_COUNT: begin
                    write_word = apply_wstrb(
                        {{(AXI_DATA_W-INDEX_W){1'b0}}, preamble_count_reg},
                        wdata_latched,
                        wstrb_latched
                    );
                    preamble_count_reg <= write_word[INDEX_W-1:0];
                end
                REG_START_OFFSET: begin
                    write_word = apply_wstrb(
                        {{(AXI_DATA_W-INDEX_W){1'b0}}, start_offset_reg},
                        wdata_latched,
                        wstrb_latched
                    );
                    start_offset_reg <= write_word[INDEX_W-1:0];
                end
                default: begin
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
