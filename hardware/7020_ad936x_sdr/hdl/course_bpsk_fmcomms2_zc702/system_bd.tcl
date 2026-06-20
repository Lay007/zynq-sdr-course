# Course overlay:
# Custom Zynq-7020 AD936x shell (xc7z020clg400-2) + deterministic BPSK burst
# core. The base shell comes from the vendor handoff project captured from the
# board image, then the course-specific modem bridge is layered on top.
#
# The RX DMA path remains intact for observation/debug. The TX DMA path is
# intentionally bypassed for the first discovery-burst design so that the
# course modem core drives the DAC FIFO directly with one reproducible burst.

set script_dir [file normalize [file dirname [info script]]]
set vendor_shell_bd [file join $script_dir "vendor_system_bd_clg400.tcl"]

source $vendor_shell_bd

# The vendor shell already instantiates the PS-side AXI-Lite interconnect.
# Seed the ADI helper with the existing MI count so the course overlay extends
# that fabric instead of attempting to recreate it from scratch.
set existing_cpu_mi [get_property CONFIG.NUM_MI [get_bd_cells axi_cpu_interconnect]]
if {$existing_cpu_mi ne ""} {
  set sys_cpu_interconnect_index $existing_cpu_mi
}

proc course_disconnect_bd_pin {pin_name} {
  set pin [get_bd_pins -quiet $pin_name]
  if {[llength $pin] == 0} {
    return
  }

  foreach net [get_bd_nets -quiet -of_objects $pin] {
    disconnect_bd_net $net $pin
  }
}

proc course_disconnect_bd_intf_pin {pin_name} {
  set pin [get_bd_intf_pins -quiet $pin_name]
  if {[llength $pin] == 0} {
    return
  }

  foreach net [get_bd_intf_nets -quiet -of_objects $pin] {
    disconnect_bd_intf_net $net $pin
  }
}

proc course_delete_bd_net {net_name} {
  delete_bd_objs -quiet [get_bd_nets -quiet $net_name]
}

proc course_delete_bd_intf_net {net_name} {
  delete_bd_objs -quiet [get_bd_intf_nets -quiet $net_name]
}

# PS-visible generic register block for the modem control/status plane.
ad_ip_instance axi_gpreg axi_gpreg_bpsk
ad_ip_parameter axi_gpreg_bpsk CONFIG.ID 1112560459
ad_ip_parameter axi_gpreg_bpsk CONFIG.NUM_OF_IO 5
ad_ip_parameter axi_gpreg_bpsk CONFIG.NUM_OF_CLK_MONS 1
ad_connect sys_cpu_clk axi_gpreg_bpsk/s_axi_aclk
ad_connect sys_cpu_resetn axi_gpreg_bpsk/s_axi_aresetn
ad_connect util_ad9361_divclk/clk_out axi_gpreg_bpsk/d_clk_0
ad_cpu_interconnect 0x79040000 axi_gpreg_bpsk

# Sample-domain bridge around the deterministic BPSK modem.
create_bd_cell -type module -reference bpsk_zynq_ber_bridge_bd bpsk_zynq_ber_gpreg_bridge_0
set_property CONFIG.MEM_FILE {bpsk_frame_bits.mem} [get_bd_cells bpsk_zynq_ber_gpreg_bridge_0]
set_property CONFIG.COEF_FILE {bpsk_rrc_tx_fir_taps.mem} [get_bd_cells bpsk_zynq_ber_gpreg_bridge_0]

ad_connect sys_cpu_clk bpsk_zynq_ber_gpreg_bridge_0/ctrl_clk
ad_connect sys_cpu_resetn bpsk_zynq_ber_gpreg_bridge_0/ctrl_resetn
ad_connect util_ad9361_divclk_reset/peripheral_aresetn bpsk_zynq_ber_gpreg_bridge_0/sample_resetn

ad_connect axi_gpreg_bpsk/up_gp_out_0 bpsk_zynq_ber_gpreg_bridge_0/gp_ctrl
ad_connect axi_gpreg_bpsk/up_gp_out_1 bpsk_zynq_ber_gpreg_bridge_0/gp_frame_bit_count
ad_connect axi_gpreg_bpsk/up_gp_out_2 bpsk_zynq_ber_gpreg_bridge_0/gp_preamble_count
ad_connect axi_gpreg_bpsk/up_gp_out_3 bpsk_zynq_ber_gpreg_bridge_0/gp_start_offset
ad_connect bpsk_zynq_ber_gpreg_bridge_0/gp_status axi_gpreg_bpsk/up_gp_in_0
ad_connect bpsk_zynq_ber_gpreg_bridge_0/gp_received_bits axi_gpreg_bpsk/up_gp_in_1
ad_connect bpsk_zynq_ber_gpreg_bridge_0/gp_total_errors axi_gpreg_bpsk/up_gp_in_2
ad_connect bpsk_zynq_ber_gpreg_bridge_0/gp_payload_errors axi_gpreg_bpsk/up_gp_in_3
ad_connect bpsk_zynq_ber_gpreg_bridge_0/gp_signature axi_gpreg_bpsk/up_gp_in_4

ad_ip_instance xlconcat bpsk_rx_sample_bus
ad_ip_parameter bpsk_rx_sample_bus CONFIG.NUM_PORTS 3
ad_ip_parameter bpsk_rx_sample_bus CONFIG.IN0_WIDTH 16
ad_ip_parameter bpsk_rx_sample_bus CONFIG.IN1_WIDTH 16
ad_ip_parameter bpsk_rx_sample_bus CONFIG.IN2_WIDTH 1

# Keep the modem bridge in the divided AD9361 sample-clock domain so the
# course FIR chain does not need to close timing at the raw 250 MHz LVDS clock.
ad_connect util_ad9361_divclk/clk_out bpsk_zynq_ber_gpreg_bridge_0/sample_clk

# Consume RX1 I/Q after the native ADC width/clock-conversion FIFO boundary.
ad_connect util_ad9361_adc_fifo/dout_data_1 bpsk_rx_sample_bus/In0
ad_connect util_ad9361_adc_fifo/dout_data_0 bpsk_rx_sample_bus/In1
ad_connect util_ad9361_adc_fifo/dout_valid_0 bpsk_rx_sample_bus/In2
ad_connect bpsk_rx_sample_bus/dout bpsk_zynq_ber_gpreg_bridge_0/rx_sample_bus

# Reuse the existing DAC FIFO boundary and inject the deterministic burst on
# its divided-clock write side instead of driving the raw DAC sample pins.
course_disconnect_bd_intf_pin axi_ad9361_dac_dma/m_axis
course_disconnect_bd_intf_pin axi_ad9361_dac_dma/m_src_axi
course_disconnect_bd_intf_pin axi_ad9361_dac_dma/s_axi
course_disconnect_bd_intf_pin axi_hp2_interconnect/S00_AXI
course_disconnect_bd_intf_pin axi_hp2_interconnect/M00_AXI
course_disconnect_bd_intf_pin sys_ps7/S_AXI_HP2
course_disconnect_bd_intf_pin util_ad9361_dac_upack/s_axis
foreach pin_name {
  axi_ad9361_dac_fifo/din_data_0
  axi_ad9361_dac_fifo/din_data_1
  axi_ad9361_dac_fifo/din_data_2
  axi_ad9361_dac_fifo/din_data_3
  axi_ad9361_dac_fifo/din_valid_in_0
  axi_ad9361_dac_fifo/din_valid_in_1
  axi_ad9361_dac_fifo/din_valid_in_2
  axi_ad9361_dac_fifo/din_valid_in_3
  axi_ad9361_dac_fifo/din_unf
  sys_concat_intc/In12
} {
  course_disconnect_bd_pin $pin_name
}
delete_bd_objs [get_bd_cells util_ad9361_dac_upack]
delete_bd_objs [get_bd_cells axi_ad9361_dac_dma]
delete_bd_objs [get_bd_cells axi_hp2_interconnect]
foreach net_name {
  axi_ad9361_dac_dma_irq
  util_ad9361_dac_upack_fifo_rd_data_0
  util_ad9361_dac_upack_fifo_rd_data_1
  util_ad9361_dac_upack_fifo_rd_data_2
  util_ad9361_dac_upack_fifo_rd_data_3
  util_ad9361_dac_upack_fifo_rd_underflow
  util_ad9361_dac_upack_fifo_rd_valid
} {
  course_delete_bd_net $net_name
}
foreach net_name {
  axi_ad9361_dac_dma_m_axis
  axi_ad9361_dac_dma_m_src_axi
  axi_cpu_interconnect_M08_AXI
  axi_hp2_interconnect_M00_AXI
} {
  course_delete_bd_intf_net $net_name
}
ad_connect GND axi_ad9361_dac_fifo/din_unf
ad_connect GND sys_concat_intc/In12

ad_ip_instance xlconstant bpsk_const_zero16
ad_ip_parameter bpsk_const_zero16 CONFIG.CONST_WIDTH 16
ad_ip_parameter bpsk_const_zero16 CONFIG.CONST_VAL 0

ad_ip_instance xlslice bpsk_tx_i
ad_ip_parameter bpsk_tx_i CONFIG.DIN_WIDTH 33
ad_ip_parameter bpsk_tx_i CONFIG.DIN_FROM 31
ad_ip_parameter bpsk_tx_i CONFIG.DIN_TO 16
ad_ip_parameter bpsk_tx_i CONFIG.DOUT_WIDTH 16

ad_ip_instance xlslice bpsk_tx_q
ad_ip_parameter bpsk_tx_q CONFIG.DIN_WIDTH 33
ad_ip_parameter bpsk_tx_q CONFIG.DIN_FROM 15
ad_ip_parameter bpsk_tx_q CONFIG.DIN_TO 0
ad_ip_parameter bpsk_tx_q CONFIG.DOUT_WIDTH 16

ad_ip_instance xlslice bpsk_tx_valid
ad_ip_parameter bpsk_tx_valid CONFIG.DIN_WIDTH 33
ad_ip_parameter bpsk_tx_valid CONFIG.DIN_FROM 32
ad_ip_parameter bpsk_tx_valid CONFIG.DIN_TO 32
ad_ip_parameter bpsk_tx_valid CONFIG.DOUT_WIDTH 1

ad_connect bpsk_zynq_ber_gpreg_bridge_0/tx_sample_bus bpsk_tx_i/Din
ad_connect bpsk_zynq_ber_gpreg_bridge_0/tx_sample_bus bpsk_tx_q/Din
ad_connect bpsk_zynq_ber_gpreg_bridge_0/tx_sample_bus bpsk_tx_valid/Din
ad_connect bpsk_tx_i/Dout axi_ad9361_dac_fifo/din_data_0
ad_connect bpsk_tx_q/Dout axi_ad9361_dac_fifo/din_data_1
ad_connect bpsk_const_zero16/dout axi_ad9361_dac_fifo/din_data_2
ad_connect bpsk_const_zero16/dout axi_ad9361_dac_fifo/din_data_3
ad_connect bpsk_tx_valid/Dout axi_ad9361_dac_fifo/din_valid_in_0
ad_connect bpsk_tx_valid/Dout axi_ad9361_dac_fifo/din_valid_in_1
ad_connect bpsk_tx_valid/Dout axi_ad9361_dac_fifo/din_valid_in_2
ad_connect bpsk_tx_valid/Dout axi_ad9361_dac_fifo/din_valid_in_3
