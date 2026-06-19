`timescale 1ns/100ps

module system_top (

  inout       [14:0]      ddr_addr,
  inout       [ 2:0]      ddr_ba,
  inout                   ddr_cas_n,
  inout                   ddr_ck_n,
  inout                   ddr_ck_p,
  inout                   ddr_cke,
  inout                   ddr_cs_n,
  inout       [ 3:0]      ddr_dm,
  inout       [31:0]      ddr_dq,
  inout       [ 3:0]      ddr_dqs_n,
  inout       [ 3:0]      ddr_dqs_p,
  inout                   ddr_odt,
  inout                   ddr_ras_n,
  inout                   ddr_reset_n,
  inout                   ddr_we_n,

  inout                   fixed_io_ddr_vrn,
  inout                   fixed_io_ddr_vrp,
  inout       [53:0]      fixed_io_mio,
  inout                   fixed_io_ps_clk,
  inout                   fixed_io_ps_porb,
  inout                   fixed_io_ps_srstb,

  input                   rx_clk_in_p,
  input                   rx_clk_in_n,
  input                   rx_frame_in_p,
  input                   rx_frame_in_n,
  input       [ 5:0]      rx_data_in_p,
  input       [ 5:0]      rx_data_in_n,
  output                  tx_clk_out_p,
  output                  tx_clk_out_n,
  output                  tx_frame_out_p,
  output                  tx_frame_out_n,
  output      [ 5:0]      tx_data_out_p,
  output      [ 5:0]      tx_data_out_n,

  output                  txnrx,
  output                  enable,

  inout                   gpio_resetb,
  inout                   gpio_sync,
  inout                   gpio_en_agc,
  inout       [ 3:0]      gpio_ctl,
  inout       [ 7:0]      gpio_status,

  output                  spi_csn,
  output                  spi_clk,
  output                  spi_mosi,
  input                   spi_miso);

wire [63:0] gpio_i;
wire [63:0] gpio_o;
wire [63:0] gpio_t;
wire [31:0] gpio_bd;
wire gpio_muxout_tx;
wire gpio_muxout_rx;

ad_iobuf #(.DATA_WIDTH(49)) i_iobuf_gpio (
  .dio_t ({gpio_t[50:49], gpio_t[46:0]}),
  .dio_i ({gpio_o[50:49], gpio_o[46:0]}),
  .dio_o ({gpio_i[50:49], gpio_i[46:0]}),
  .dio_p ({ gpio_muxout_tx,
            gpio_muxout_rx,
            gpio_resetb,
            gpio_sync,
            gpio_en_agc,
            gpio_ctl,
            gpio_status,
            gpio_bd}));

assign gpio_i[63:51] = gpio_o[63:51];
assign gpio_i[48:47] = gpio_o[48:47];

system_wrapper i_system_wrapper (
  .ddr_addr (ddr_addr),
  .ddr_ba (ddr_ba),
  .ddr_cas_n (ddr_cas_n),
  .ddr_ck_n (ddr_ck_n),
  .ddr_ck_p (ddr_ck_p),
  .ddr_cke (ddr_cke),
  .ddr_cs_n (ddr_cs_n),
  .ddr_dm (ddr_dm),
  .ddr_dq (ddr_dq),
  .ddr_dqs_n (ddr_dqs_n),
  .ddr_dqs_p (ddr_dqs_p),
  .ddr_odt (ddr_odt),
  .ddr_ras_n (ddr_ras_n),
  .ddr_reset_n (ddr_reset_n),
  .ddr_we_n (ddr_we_n),
  .fixed_io_ddr_vrn (fixed_io_ddr_vrn),
  .fixed_io_ddr_vrp (fixed_io_ddr_vrp),
  .fixed_io_mio (fixed_io_mio),
  .fixed_io_ps_clk (fixed_io_ps_clk),
  .fixed_io_ps_porb (fixed_io_ps_porb),
  .fixed_io_ps_srstb (fixed_io_ps_srstb),
  .gpio_i (gpio_i),
  .gpio_o (gpio_o),
  .gpio_t (gpio_t),
  .rx_clk_in_n (rx_clk_in_n),
  .rx_clk_in_p (rx_clk_in_p),
  .rx_data_in_n (rx_data_in_n),
  .rx_data_in_p (rx_data_in_p),
  .rx_frame_in_n (rx_frame_in_n),
  .rx_frame_in_p (rx_frame_in_p),
  .spi0_csn_i (1'b1),
  .spi0_csn_0_o (spi_csn),
  .spi0_csn_1_o (),
  .spi0_csn_2_o (),
  .spi0_sdi_i (spi_miso),
  .spi0_sdo_i (1'b0),
  .spi0_sdo_o (spi_mosi),
  .spi0_clk_i (1'b0),
  .spi0_clk_o (spi_clk),
  .tx_clk_out_n (tx_clk_out_n),
  .tx_clk_out_p (tx_clk_out_p),
  .tx_data_out_n (tx_data_out_n),
  .tx_data_out_p (tx_data_out_p),
  .tx_frame_out_n (tx_frame_out_n),
  .tx_frame_out_p (tx_frame_out_p),
  .tdd_sync_i (1'b0),
  .tdd_sync_o (),
  .tdd_sync_t (),
  .spi1_clk_i (1'b0),
  .spi1_clk_o (),
  .spi1_csn_i (1'b1),
  .spi1_csn_0_o (),
  .spi1_csn_1_o (),
  .spi1_csn_2_o (),
  .spi1_sdo_i (),
  .spi1_sdo_o (),
  .spi1_sdi_i (1'b0),
  .enable (enable),
  .txnrx (txnrx),
  .up_enable (gpio_o[47]),
  .up_txnrx (gpio_o[48]));

endmodule
