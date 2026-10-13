`timescale 1ns/1ps
// Block-design wrapper of ofdm_axi_modem for a PS + AXI DMA fabric loopback
// (issue #48, verification stage 3 without the RF path).
//
// The X_INTERFACE attributes make the ports appear as buses when the module is
// added to a Vivado block design as a module reference:
//   S_AXI      AXI4-Lite control (the modem register map, 64 bytes)
//   S_AXIS_TX  bits in   (one QPSK bit pair per byte, 48 per OFDM symbol;
//              tlast is ignored, the modem frames by count) <- DMA MM2S
//   M_AXIS_RX  bits out  ({data_index[5:0], bits[1:0]}, 48 per symbol, tlast on
//              the 48th, so one DMA S2MM transfer per symbol) -> DMA S2MM
// The 32-bit sample streams stay inside: the modem's TX output feeds its own RX
// input, with no channel. Replacing this loopback with the AD9361 sample path
// (and a clock-domain crossing) is the step that needs the board.
module ofdm_axi_modem_vivado_wrapper #(
    parameter integer CE_TRAIN_SYMBOLS = 1
) (
    (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME S_AXI, PROTOCOL AXI4LITE, DATA_WIDTH 32, ADDR_WIDTH 32, FREQ_HZ 100000000" *)
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWADDR" *)
    input  wire [31:0] s_axi_awaddr,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWVALID" *)
    input  wire        s_axi_awvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWREADY" *)
    output wire        s_axi_awready,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI WDATA" *)
    input  wire [31:0] s_axi_wdata,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI WSTRB" *)
    input  wire [3:0]  s_axi_wstrb,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI WVALID" *)
    input  wire        s_axi_wvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI WREADY" *)
    output wire        s_axi_wready,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI BRESP" *)
    output wire [1:0]  s_axi_bresp,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI BVALID" *)
    output wire        s_axi_bvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI BREADY" *)
    input  wire        s_axi_bready,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARADDR" *)
    input  wire [31:0] s_axi_araddr,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARVALID" *)
    input  wire        s_axi_arvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARREADY" *)
    output wire        s_axi_arready,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *)
    output wire [31:0] s_axi_rdata,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RRESP" *)
    output wire [1:0]  s_axi_rresp,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RVALID" *)
    output wire        s_axi_rvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RREADY" *)
    input  wire        s_axi_rready,

    (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME S_AXIS_TX, TDATA_NUM_BYTES 1, HAS_TLAST 1, HAS_TKEEP 0, HAS_TSTRB 0, FREQ_HZ 100000000" *)
    (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 S_AXIS_TX TDATA" *)
    input  wire [7:0]  s_axis_tx_tdata,
    (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 S_AXIS_TX TVALID" *)
    input  wire        s_axis_tx_tvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 S_AXIS_TX TREADY" *)
    output wire        s_axis_tx_tready,
    (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 S_AXIS_TX TLAST" *)
    input  wire        s_axis_tx_tlast,

    (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME M_AXIS_RX, TDATA_NUM_BYTES 1, HAS_TLAST 1, HAS_TKEEP 0, HAS_TSTRB 0, FREQ_HZ 100000000" *)
    (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 M_AXIS_RX TDATA" *)
    output wire [7:0]  m_axis_rx_tdata,
    (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 M_AXIS_RX TVALID" *)
    output wire        m_axis_rx_tvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 M_AXIS_RX TREADY" *)
    input  wire        m_axis_rx_tready,
    (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 M_AXIS_RX TLAST" *)
    output wire        m_axis_rx_tlast,

    (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ACLK, ASSOCIATED_BUSIF S_AXI:S_AXIS_TX:M_AXIS_RX, ASSOCIATED_RESET aresetn, FREQ_HZ 100000000" *)
    (* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 ACLK CLK" *)
    input  wire        aclk,
    (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ARESETN, POLARITY ACTIVE_LOW" *)
    (* X_INTERFACE_INFO = "xilinx.com:signal:reset:1.0 ARESETN RST" *)
    input  wire        aresetn
);

    wire        loop_valid;
    wire        loop_ready;
    wire [31:0] loop_data;
    wire        loop_last;

    ofdm_axi_modem #(
        .AXI_ADDR_W(6),
        .AXI_DATA_W(32),
        .CE_TRAIN_SYMBOLS(CE_TRAIN_SYMBOLS)
    ) modem (
        .aclk(aclk),
        .aresetn(aresetn),
        .s_axis_tx_tvalid(s_axis_tx_tvalid),
        .s_axis_tx_tready(s_axis_tx_tready),
        .s_axis_tx_tdata(s_axis_tx_tdata),
        .s_axis_tx_tlast(s_axis_tx_tlast),
        .m_axis_tx_tvalid(loop_valid),
        .m_axis_tx_tready(loop_ready),
        .m_axis_tx_tdata(loop_data),
        .m_axis_tx_tlast(loop_last),
        .s_axis_rx_tvalid(loop_valid),
        .s_axis_rx_tready(loop_ready),
        .s_axis_rx_tdata(loop_data),
        .s_axis_rx_tlast(loop_last),
        .m_axis_rx_tvalid(m_axis_rx_tvalid),
        .m_axis_rx_tready(m_axis_rx_tready),
        .m_axis_rx_tdata(m_axis_rx_tdata),
        .m_axis_rx_tlast(m_axis_rx_tlast),
        .s_axi_awaddr(s_axi_awaddr[5:0]),
        .s_axi_awvalid(s_axi_awvalid),
        .s_axi_awready(s_axi_awready),
        .s_axi_wdata(s_axi_wdata),
        .s_axi_wstrb(s_axi_wstrb),
        .s_axi_wvalid(s_axi_wvalid),
        .s_axi_wready(s_axi_wready),
        .s_axi_bresp(s_axi_bresp),
        .s_axi_bvalid(s_axi_bvalid),
        .s_axi_bready(s_axi_bready),
        .s_axi_araddr(s_axi_araddr[5:0]),
        .s_axi_arvalid(s_axi_arvalid),
        .s_axi_arready(s_axi_arready),
        .s_axi_rdata(s_axi_rdata),
        .s_axi_rresp(s_axi_rresp),
        .s_axi_rvalid(s_axi_rvalid),
        .s_axi_rready(s_axi_rready)
    );

endmodule
