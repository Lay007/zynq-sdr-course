# Course overlay:
# Custom Zynq-7020 AD936x shell (xc7z020clg400-2) + deterministic BPSK burst
# core. The base shell comes from the vendor handoff project captured from the
# board image, then the course-specific modem bridge is layered on top.
#
# The RX DMA path remains intact for observation/debug. The TX DMA-side Linux
# probe contract also remains intact as well: the safe default mode is
# "gpreg_only", while the intermediate "bridge_rx_only" mode reattaches the
# sample-domain bridge and RX tap without taking ownership of the DAC path.

set script_dir [file normalize [file dirname [info script]]]
set vendor_shell_bd [file join $script_dir "vendor_system_bd_clg400.tcl"]
set overlay_mode "gpreg_only"
if {[info exists ::env(COURSE_OVERLAY_MODE)]} {
  set overlay_mode $::env(COURSE_OVERLAY_MODE)
}

source $vendor_shell_bd

# The vendor shell already instantiates the PS-side AXI-Lite interconnect.
# Seed the ADI helper with the existing MI count so the course overlay extends
# that fabric instead of attempting to recreate it from scratch.
set existing_cpu_mi [get_property CONFIG.NUM_MI [get_bd_cells axi_cpu_interconnect]]
if {$existing_cpu_mi ne ""} {
  set sys_cpu_interconnect_index $existing_cpu_mi
}

if {$overlay_mode eq "vendor_only"} {
  puts "COURSE_OVERLAY_MODE=vendor_only: leaving the vendor shell unmodified."
  return
}

if {$overlay_mode ne "gpreg_only" && $overlay_mode ne "bridge_rx_only"} {
  error "Unsupported COURSE_OVERLAY_MODE '$overlay_mode'. Expected vendor_only, gpreg_only or bridge_rx_only."
}

# PS-visible generic register block for the modem control/status plane.
ad_ip_instance axi_gpreg axi_gpreg_bpsk
ad_ip_parameter axi_gpreg_bpsk CONFIG.ID 1112560459
ad_ip_parameter axi_gpreg_bpsk CONFIG.NUM_OF_IO 5
ad_ip_parameter axi_gpreg_bpsk CONFIG.NUM_OF_CLK_MONS 0
ad_connect sys_cpu_clk axi_gpreg_bpsk/s_axi_aclk
ad_connect sys_cpu_resetn axi_gpreg_bpsk/s_axi_aresetn
ad_cpu_interconnect 0x79040000 axi_gpreg_bpsk

# Minimal gpreg-only bring-up image: keep the PS-visible control/status block,
# but drive its live status inputs from constants while the AD9361 shell
# compatibility is re-established. This isolates the boot-time impact of the
# larger sample-domain bridge and RX tap logic.
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
  return
}

# Intermediate bridge_rx_only mode: reattach the sample-domain BER bridge and
# the RX1 I/Q tap while still leaving the Linux-visible DAC path untouched.
set bpsk_bridge_bd [ create_bd_cell -type module -reference bpsk_zynq_ber_bridge_bd bpsk_bridge_bd ]
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

set bpsk_rx_sample_concat [ create_bd_cell -type ip -vlnv xilinx.com:ip:xlconcat:2.1 bpsk_rx_sample_concat ]
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
