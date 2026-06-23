# Shared Block Design overlay helper for the course-owned BPSK reintegration
# path. This file assumes the vendor AD9361 shell is already open as the
# current block design and that the ADI Tcl helpers are available.

proc course_bpsk_overlay_mode {} {
  set overlay_mode "gpreg_only"
  if {[info exists ::env(COURSE_OVERLAY_MODE)]} {
    set overlay_mode $::env(COURSE_OVERLAY_MODE)
  }
  return $overlay_mode
}

proc course_disconnect_bd_pin {pin_path} {
  set pin_obj [get_bd_pins -quiet $pin_path]
  if {$pin_obj eq ""} {
    error "Missing BD pin while disconnecting overlay sink: $pin_path"
  }

  foreach net_obj [get_bd_nets -quiet -of_objects $pin_obj] {
    disconnect_bd_net $net_obj $pin_obj
  }
}

proc course_bpsk_apply_overlay {overlay_mode} {
  if {$overlay_mode ne "vendor_only" && $overlay_mode ne "gpreg_only" && $overlay_mode ne "bridge_rx_only" && $overlay_mode ne "bridge_txrx_mux"} {
    error "Unsupported COURSE_OVERLAY_MODE '$overlay_mode'. Expected vendor_only, gpreg_only, bridge_rx_only or bridge_txrx_mux."
  }

  # The recovered CLG400 Tcl shell is close to the working vendor snapshot,
  # but the generated sources carried a preset that forces PS MIO14/15 back to
  # Vivado defaults. Keep the explicit directions before any overlay branch so
  # XSA diffs stay focused on the remaining true deltas.
  set_property -dict [list \
    CONFIG.preset {None} \
    CONFIG.PCW_MIO_14_DIRECTION {in} \
    CONFIG.PCW_MIO_15_DIRECTION {out} \
  ] [get_bd_cells sys_ps7]

  # The vendor shell already instantiates the PS-side AXI-Lite interconnect.
  # Seed the ADI helper with the existing MI count so the course overlay
  # extends that fabric instead of attempting to recreate it from scratch.
  set existing_cpu_mi [get_property CONFIG.NUM_MI [get_bd_cells axi_cpu_interconnect]]
  if {$existing_cpu_mi ne ""} {
    set ::sys_cpu_interconnect_index $existing_cpu_mi
  }

  if {$overlay_mode eq "vendor_only"} {
    puts "COURSE_OVERLAY_MODE=vendor_only: leaving the vendor shell unmodified."
    return
  }

  # PS-visible generic register block for the modem control/status plane.
  ad_ip_instance axi_gpreg axi_gpreg_bpsk
  ad_ip_parameter axi_gpreg_bpsk CONFIG.ID 1112560459
  ad_ip_parameter axi_gpreg_bpsk CONFIG.NUM_OF_IO 8
  ad_ip_parameter axi_gpreg_bpsk CONFIG.NUM_OF_CLK_MONS 0
  ad_connect sys_cpu_clk axi_gpreg_bpsk/s_axi_aclk
  ad_connect sys_cpu_resetn axi_gpreg_bpsk/s_axi_aresetn
  ad_cpu_interconnect 0x79040000 axi_gpreg_bpsk

  # Minimal gpreg-only bring-up image: keep the PS-visible control/status
  # block, but drive its live status inputs from constants while the AD9361
  # shell compatibility is re-established.
  ad_ip_instance xlconstant bpsk_const_zero32
  ad_ip_parameter bpsk_const_zero32 CONFIG.CONST_WIDTH 32
  ad_ip_parameter bpsk_const_zero32 CONFIG.CONST_VAL 0

  ad_ip_instance xlconstant bpsk_const_signature32
  ad_ip_parameter bpsk_const_signature32 CONFIG.CONST_WIDTH 32
  ad_ip_parameter bpsk_const_signature32 CONFIG.CONST_VAL 1112560459

  if {$overlay_mode eq "gpreg_only"} {
    ad_connect bpsk_const_zero32/dout axi_gpreg_bpsk/up_gp_in_0
    ad_connect bpsk_const_zero32/dout axi_gpreg_bpsk/up_gp_in_1
    ad_connect bpsk_const_zero32/dout axi_gpreg_bpsk/up_gp_in_2
    ad_connect bpsk_const_zero32/dout axi_gpreg_bpsk/up_gp_in_3
    ad_connect bpsk_const_signature32/dout axi_gpreg_bpsk/up_gp_in_4
    ad_connect bpsk_const_zero32/dout axi_gpreg_bpsk/up_gp_in_5
    ad_connect bpsk_const_zero32/dout axi_gpreg_bpsk/up_gp_in_6
    ad_connect bpsk_const_zero32/dout axi_gpreg_bpsk/up_gp_in_7
    return
  }

  # Intermediate bridge mode: reattach the sample-domain BER bridge and the
  # RX1 I/Q tap while still keeping the vendor DAC shell intact.
  set bpsk_bridge_bd [create_bd_cell -type module -reference bpsk_zynq_ber_bridge_bd bpsk_bridge_bd]
  ad_connect sys_cpu_clk bpsk_bridge_bd/ctrl_clk
  ad_connect sys_cpu_resetn bpsk_bridge_bd/ctrl_resetn
  ad_connect util_ad9361_divclk/clk_out bpsk_bridge_bd/sample_clk
  ad_connect util_ad9361_divclk_reset/peripheral_aresetn bpsk_bridge_bd/sample_resetn

  ad_connect axi_gpreg_bpsk/up_gp_out_0 bpsk_bridge_bd/gp_ctrl
  ad_connect axi_gpreg_bpsk/up_gp_out_1 bpsk_bridge_bd/gp_frame_bit_count
  ad_connect axi_gpreg_bpsk/up_gp_out_2 bpsk_bridge_bd/gp_preamble_count
  ad_connect axi_gpreg_bpsk/up_gp_out_3 bpsk_bridge_bd/gp_start_offset

  ad_connect bpsk_bridge_bd/gp_status axi_gpreg_bpsk/up_gp_in_0
  ad_connect bpsk_bridge_bd/gp_received_bits axi_gpreg_bpsk/up_gp_in_1
  ad_connect bpsk_bridge_bd/gp_total_errors axi_gpreg_bpsk/up_gp_in_2
  ad_connect bpsk_bridge_bd/gp_payload_errors axi_gpreg_bpsk/up_gp_in_3
  ad_connect bpsk_bridge_bd/gp_signature axi_gpreg_bpsk/up_gp_in_4
  ad_connect bpsk_bridge_bd/gp_tx_valid_count axi_gpreg_bpsk/up_gp_in_5
  ad_connect bpsk_bridge_bd/gp_rx_valid_count axi_gpreg_bpsk/up_gp_in_6
  ad_connect bpsk_bridge_bd/gp_capture_debug axi_gpreg_bpsk/up_gp_in_7

  set bpsk_rx_sample_concat [create_bd_cell -type ip -vlnv xilinx.com:ip:xlconcat:2.1 bpsk_rx_sample_concat]
  set_property -dict [list \
    CONFIG.NUM_PORTS {3} \
    CONFIG.IN0_WIDTH {16} \
    CONFIG.IN1_WIDTH {16} \
    CONFIG.IN2_WIDTH {1} \
  ] $bpsk_rx_sample_concat
  ad_connect util_ad9361_adc_fifo/dout_data_1 bpsk_rx_sample_concat/In0
  ad_connect util_ad9361_adc_fifo/dout_data_0 bpsk_rx_sample_concat/In1
  ad_connect util_ad9361_adc_fifo/dout_valid_0 bpsk_rx_sample_concat/In2
  ad_connect bpsk_rx_sample_concat/dout bpsk_bridge_bd/rx_sample_bus

  if {$overlay_mode eq "bridge_rx_only"} {
    return
  }

  # Final staged bridge mode for the first live RF discovery burst: keep the
  # vendor DMA/TX chain instantiated, but steer the DAC FIFO input over to the
  # BPSK bridge only while its burst path is active.
  set course_dac_fifo_source_mux [create_bd_cell -type module -reference course_dac_fifo_source_mux course_dac_fifo_source_mux]
  ad_connect bpsk_bridge_bd/tx_path_active course_dac_fifo_source_mux/select_bpsk
  ad_connect bpsk_bridge_bd/tx_sample_bus course_dac_fifo_source_mux/bpsk_tx_sample_bus

  course_disconnect_bd_pin axi_ad9361_dac_fifo/din_data_0
  course_disconnect_bd_pin axi_ad9361_dac_fifo/din_data_1
  course_disconnect_bd_pin axi_ad9361_dac_fifo/din_data_2
  course_disconnect_bd_pin axi_ad9361_dac_fifo/din_data_3
  course_disconnect_bd_pin axi_ad9361_dac_fifo/din_unf
  course_disconnect_bd_pin axi_ad9361_dac_fifo/din_valid_in_0
  course_disconnect_bd_pin axi_ad9361_dac_fifo/din_valid_in_1
  course_disconnect_bd_pin axi_ad9361_dac_fifo/din_valid_in_2
  course_disconnect_bd_pin axi_ad9361_dac_fifo/din_valid_in_3

  ad_connect util_ad9361_dac_upack/fifo_rd_data_0 course_dac_fifo_source_mux/vendor_data_0
  ad_connect util_ad9361_dac_upack/fifo_rd_data_1 course_dac_fifo_source_mux/vendor_data_1
  ad_connect util_ad9361_dac_upack/fifo_rd_data_2 course_dac_fifo_source_mux/vendor_data_2
  ad_connect util_ad9361_dac_upack/fifo_rd_data_3 course_dac_fifo_source_mux/vendor_data_3
  ad_connect util_ad9361_dac_upack/fifo_rd_valid course_dac_fifo_source_mux/vendor_valid
  ad_connect util_ad9361_dac_upack/fifo_rd_underflow course_dac_fifo_source_mux/vendor_unf

  ad_connect course_dac_fifo_source_mux/fifo_data_0 axi_ad9361_dac_fifo/din_data_0
  ad_connect course_dac_fifo_source_mux/fifo_data_1 axi_ad9361_dac_fifo/din_data_1
  ad_connect course_dac_fifo_source_mux/fifo_data_2 axi_ad9361_dac_fifo/din_data_2
  ad_connect course_dac_fifo_source_mux/fifo_data_3 axi_ad9361_dac_fifo/din_data_3
  ad_connect course_dac_fifo_source_mux/fifo_unf axi_ad9361_dac_fifo/din_unf
  ad_connect course_dac_fifo_source_mux/fifo_valid axi_ad9361_dac_fifo/din_valid_in_0
  ad_connect course_dac_fifo_source_mux/fifo_valid axi_ad9361_dac_fifo/din_valid_in_1
  ad_connect course_dac_fifo_source_mux/fifo_valid axi_ad9361_dac_fifo/din_valid_in_2
  ad_connect course_dac_fifo_source_mux/fifo_valid axi_ad9361_dac_fifo/din_valid_in_3
}
