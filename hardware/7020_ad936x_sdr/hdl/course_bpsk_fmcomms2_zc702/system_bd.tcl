# Course overlay:
# Custom Zynq-7020 AD936x shell (xc7z020clg400-2) + deterministic BPSK burst
# core. The base shell comes from the vendor handoff project captured from the
# board image, then the course-specific modem bridge is layered on top.
#
# The RX DMA path remains intact for observation/debug. The TX DMA-side Linux
# probe contract also remains intact: the course modem overrides only the DAC
# FIFO write-side sample stream, while the original DAC DMA / upack chain stays
# instantiated so the stock device tree still matches the PL shell.

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

# PS-visible generic register block for the modem control/status plane.
ad_ip_instance axi_gpreg axi_gpreg_bpsk
ad_ip_parameter axi_gpreg_bpsk CONFIG.ID 1112560459
ad_ip_parameter axi_gpreg_bpsk CONFIG.NUM_OF_IO 5
ad_ip_parameter axi_gpreg_bpsk CONFIG.NUM_OF_CLK_MONS 0
ad_connect sys_cpu_clk axi_gpreg_bpsk/s_axi_aclk
ad_connect sys_cpu_resetn axi_gpreg_bpsk/s_axi_aresetn
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

# Reuse the existing DAC FIFO boundary and override only its divided-clock
# write-side sample inputs. The stock Linux image still probes the DAC DMA and
# util_upack path, so keep those blocks alive and insert a small mux before the
# FIFO instead of deleting the TX DMA fabric from the PL shell.
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
} {
  course_disconnect_bd_pin $pin_name
}

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

create_bd_cell -type module -reference course_dac_fifo_source_mux bpsk_dac_fifo_mux

ad_connect bpsk_zynq_ber_gpreg_bridge_0/tx_sample_bus bpsk_tx_i/Din
ad_connect bpsk_zynq_ber_gpreg_bridge_0/tx_sample_bus bpsk_tx_q/Din
ad_connect bpsk_zynq_ber_gpreg_bridge_0/tx_sample_bus bpsk_tx_valid/Din

ad_connect VCC bpsk_dac_fifo_mux/select_bpsk
ad_connect util_ad9361_dac_upack/fifo_rd_data_0 bpsk_dac_fifo_mux/vendor_data_0
ad_connect util_ad9361_dac_upack/fifo_rd_data_1 bpsk_dac_fifo_mux/vendor_data_1
ad_connect util_ad9361_dac_upack/fifo_rd_data_2 bpsk_dac_fifo_mux/vendor_data_2
ad_connect util_ad9361_dac_upack/fifo_rd_data_3 bpsk_dac_fifo_mux/vendor_data_3
ad_connect util_ad9361_dac_upack/fifo_rd_valid bpsk_dac_fifo_mux/vendor_valid
ad_connect util_ad9361_dac_upack/fifo_rd_underflow bpsk_dac_fifo_mux/vendor_unf
ad_connect bpsk_tx_i/Dout bpsk_dac_fifo_mux/bpsk_data_0
ad_connect bpsk_tx_q/Dout bpsk_dac_fifo_mux/bpsk_data_1
ad_connect bpsk_const_zero16/dout bpsk_dac_fifo_mux/bpsk_data_2
ad_connect bpsk_const_zero16/dout bpsk_dac_fifo_mux/bpsk_data_3
ad_connect bpsk_tx_valid/Dout bpsk_dac_fifo_mux/bpsk_valid
ad_connect GND bpsk_dac_fifo_mux/bpsk_unf

ad_connect bpsk_dac_fifo_mux/fifo_data_0 axi_ad9361_dac_fifo/din_data_0
ad_connect bpsk_dac_fifo_mux/fifo_data_1 axi_ad9361_dac_fifo/din_data_1
ad_connect bpsk_dac_fifo_mux/fifo_data_2 axi_ad9361_dac_fifo/din_data_2
ad_connect bpsk_dac_fifo_mux/fifo_data_3 axi_ad9361_dac_fifo/din_data_3
ad_connect bpsk_dac_fifo_mux/fifo_valid axi_ad9361_dac_fifo/din_valid_in_0
ad_connect bpsk_dac_fifo_mux/fifo_valid axi_ad9361_dac_fifo/din_valid_in_1
ad_connect bpsk_dac_fifo_mux/fifo_valid axi_ad9361_dac_fifo/din_valid_in_2
ad_connect bpsk_dac_fifo_mux/fifo_valid axi_ad9361_dac_fifo/din_valid_in_3
ad_connect bpsk_dac_fifo_mux/fifo_unf axi_ad9361_dac_fifo/din_unf
