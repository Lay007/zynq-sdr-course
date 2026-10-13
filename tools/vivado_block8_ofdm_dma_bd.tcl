# Issue #48: PS + AXI DMA + OFDM modem Block Design, built to a bitstream.
#
# usage: vivado -mode batch -source vivado_block8_ofdm_dma_bd.tcl
#          -tclargs <build_dir> <ps7_params.tcl> <report_dir> <ce_train_symbols>
#
# The same recipe as the Lab 5.12 mailbox (tools/vivado_block5_mailbox_bd.tcl):
# the board's own PS7 settings, then the design's additions. Data path:
#
#   DDR -> S_AXI_HP0 -> AXI DMA MM2S -> modem S_AXIS_TX (bit pairs)
#          modem TX samples -> modem RX samples (fabric loopback in the wrapper)
#   modem M_AXIS_RX (decoded bits) -> AXI DMA S2MM -> S_AXI_HP0 -> DDR
#
# Control: M_AXI_GP0 -> modem S_AXI (registers) and DMA S_AXI_LITE. Both DMA
# interrupts go to IRQ_F2P. One clock: FCLK_CLK0 at 100 MHz.

if {[llength $argv] != 4} {
    error "usage: vivado_block8_ofdm_dma_bd.tcl <build_dir> <ps7_params.tcl> <report_dir> <ce_train_symbols>"
}
set build_dir [file normalize [lindex $argv 0]]
set params_file [file normalize [lindex $argv 1]]
set report_dir [file normalize [lindex $argv 2]]
set train_symbols [lindex $argv 3]
set root_dir [file normalize [file join [file dirname [info script]] ".."]]
file mkdir $report_dir

set_param general.maxThreads 1
set proj_dir [file join $build_dir proj]
create_project ofdm_dma $proj_dir -part xc7z020clg400-2 -force
add_files [glob [file join $root_dir blocks/block_08_modulation_and_synchronization/rtl ofdm_*.v]]
update_compile_order -fileset sources_1

create_bd_design "ofdm_dma_bd"

# Zynq PS with the board's DDR/MIO/peripheral settings (no board preset).
create_bd_cell -type ip -vlnv xilinx.com:ip:processing_system7:5.5 processing_system7_0
apply_bd_automation -rule xilinx.com:bd_rule:processing_system7 \
    -config {make_external "FIXED_IO, DDR" apply_board_preset "0"} \
    [get_bd_cells processing_system7_0]
source $params_file
set ps [get_bd_cells processing_system7_0]
set applied 0
set skipped {}
foreach {name value} $ps7_board_params {
    if {[catch {set_property CONFIG.$name $value $ps}]} {
        lappend skipped $name
    } else {
        incr applied
    }
}
# Additions: one AXI master for control, one high-performance slave port for the
# DMA, one PL clock with its reset, and fabric interrupts.
set_property -dict [list \
    CONFIG.PCW_USE_M_AXI_GP0 {1} \
    CONFIG.PCW_USE_S_AXI_HP0 {1} \
    CONFIG.PCW_EN_CLK0_PORT {1} \
    CONFIG.PCW_EN_RST0_PORT {1} \
    CONFIG.PCW_FPGA0_PERIPHERAL_FREQMHZ {100} \
    CONFIG.PCW_USE_FABRIC_INTERRUPT {1} \
    CONFIG.PCW_IRQ_F2P_INTR {1}] $ps

# AXI DMA in simple (register) mode with 8-bit streams: one byte per bit pair.
create_bd_cell -type ip -vlnv xilinx.com:ip:axi_dma:7.1 axi_dma_0
set_property -dict [list \
    CONFIG.c_include_sg {0} \
    CONFIG.c_sg_length_width {16} \
    CONFIG.c_m_axis_mm2s_tdata_width {8} \
    CONFIG.c_s_axis_s2mm_tdata_width {8} \
    CONFIG.c_mm2s_burst_size {16} \
    CONFIG.c_s2mm_burst_size {16}] [get_bd_cells axi_dma_0]

# The modem as a module reference (the wrapper iverilog elaborates in CI).
create_bd_cell -type module -reference ofdm_axi_modem_vivado_wrapper modem_0
set_property CONFIG.CE_TRAIN_SYMBOLS $train_symbols [get_bd_cells modem_0]

# Control: M_AXI_GP0 -> modem and DMA registers. Data: DMA masters -> HP0.
apply_bd_automation -rule xilinx.com:bd_rule:axi4 \
    -config {Master "/processing_system7_0/M_AXI_GP0" Clk "Auto"} \
    [get_bd_intf_pins modem_0/S_AXI]
# The automation gives the modem the whole 1 GB GP0 window; shrink it to 4K (it
# decodes 64 bytes) now, or the DMA registers find no free aperture and Vivado
# silently excludes them from the address map.
set_property range 4K [get_bd_addr_segs {processing_system7_0/Data/SEG_modem_0_reg0}]
apply_bd_automation -rule xilinx.com:bd_rule:axi4 \
    -config {Master "/processing_system7_0/M_AXI_GP0" Clk "Auto"} \
    [get_bd_intf_pins axi_dma_0/S_AXI_LITE]
# The first DMA master is connected from the slave side (Vivado finds no target
# the other way round); the second joins the SmartConnect that call creates.
apply_bd_automation -rule xilinx.com:bd_rule:axi4 \
    -config {Clk_master {Auto} Clk_slave {Auto} Clk_xbar {Auto} Master {/axi_dma_0/M_AXI_MM2S} \
             Slave {/processing_system7_0/S_AXI_HP0} ddr_seg {Auto} intc_ip {New AXI SmartConnect} master_apm {0}} \
    [get_bd_intf_pins processing_system7_0/S_AXI_HP0]
apply_bd_automation -rule xilinx.com:bd_rule:axi4 \
    -config {Clk_master {Auto} Clk_slave {Auto} Clk_xbar {Auto} Master {/axi_dma_0/M_AXI_S2MM} \
             Slave {/processing_system7_0/S_AXI_HP0} ddr_seg {Auto} intc_ip {Auto} master_apm {0}} \
    [get_bd_intf_pins axi_dma_0/M_AXI_S2MM]

# Streams.
connect_bd_intf_net [get_bd_intf_pins axi_dma_0/M_AXIS_MM2S] [get_bd_intf_pins modem_0/S_AXIS_TX]
connect_bd_intf_net [get_bd_intf_pins modem_0/M_AXIS_RX] [get_bd_intf_pins axi_dma_0/S_AXIS_S2MM]

# Interrupts: MM2S and S2MM done -> IRQ_F2P[1:0].
create_bd_cell -type ip -vlnv xilinx.com:ip:xlconcat:2.1 irq_concat
set_property CONFIG.NUM_PORTS {2} [get_bd_cells irq_concat]
connect_bd_net [get_bd_pins axi_dma_0/mm2s_introut] [get_bd_pins irq_concat/In0]
connect_bd_net [get_bd_pins axi_dma_0/s2mm_introut] [get_bd_pins irq_concat/In1]
connect_bd_net [get_bd_pins irq_concat/dout] [get_bd_pins processing_system7_0/IRQ_F2P]

assign_bd_address
# Both register blocks must be visible to the PS; an excluded segment is only a warning.
foreach required {SEG_modem_0_reg0 SEG_axi_dma_0_Reg} {
    if {[llength [get_bd_addr_segs processing_system7_0/Data/$required]] != 1} {
        error "$required is missing from the PS address map"
    }
}
if {[llength [get_bd_addr_segs -excluded -of_objects [get_bd_addr_spaces processing_system7_0/Data]]] != 0} {
    error "a slave segment was excluded from the PS address map"
}
validate_bd_design
save_bd_design

set fclk0 [get_property CONFIG.PCW_FPGA0_PERIPHERAL_FREQMHZ $ps]
set fclk0_actual [get_property CONFIG.PCW_ACT_FPGA0_PERIPHERAL_FREQMHZ $ps]
set segments {}
foreach seg [get_bd_addr_segs -of_objects [get_bd_addr_spaces processing_system7_0/Data]] {
    lappend segments [list [get_property NAME $seg] [get_property OFFSET $seg] [get_property RANGE $seg]]
}

set bd_file [get_files ofdm_dma_bd.bd]
make_wrapper -files $bd_file -top
add_files -norecurse [file join $proj_dir ofdm_dma.gen sources_1 bd ofdm_dma_bd hdl ofdm_dma_bd_wrapper.v]
set_property top ofdm_dma_bd_wrapper [current_fileset]
update_compile_order -fileset sources_1

# One job at a time (memory).
launch_runs impl_1 -to_step write_bitstream -jobs 1
wait_on_run impl_1
if {[get_property PROGRESS [get_runs impl_1]] ne "100%"} {
    error "implementation did not complete: [get_property STATUS [get_runs impl_1]]"
}
open_run impl_1
report_utilization -file [file join $report_dir ofdm_dma_utilization.rpt]
report_utilization -hierarchical -hierarchical_depth 3 -file [file join $report_dir ofdm_dma_utilization_hierarchical.rpt]
report_timing_summary -delay_type max -max_paths 5 -file [file join $report_dir ofdm_dma_timing_summary.rpt]
report_drc -file [file join $report_dir ofdm_dma_drc.rpt]
write_hw_platform -fixed -include_bit -force -file [file join $build_dir ofdm_dma_bd_wrapper.xsa]

set out [open [file join $report_dir ofdm_dma_build.json] w]
puts $out "{"
puts $out "  \"segments\": \["
set first 1
foreach s $segments {
    if {!$first} { puts $out "," }
    puts -nonewline $out "    {\"name\": \"[lindex $s 0]\", \"offset\": \"[lindex $s 1]\", \"range\": \"[lindex $s 2]\"}"
    set first 0
}
puts $out ""
puts $out "  \],"
puts $out "  \"ce_train_symbols\": $train_symbols,"
puts $out "  \"fclk0_requested_mhz\": \"$fclk0\","
puts $out "  \"fclk0_actual_mhz\": \"$fclk0_actual\","
puts $out "  \"ps7_params_written\": $applied,"
puts $out "  \"ps7_params_write_errors\": [llength $skipped],"
puts $out "  \"bitstream\": \"[file tail [get_property DIRECTORY [get_runs impl_1]]]/ofdm_dma_bd_wrapper.bit\","
puts $out "  \"vivado\": \"[version -short]\""
puts $out "}"
close $out
puts "OFDM_DMA_BD built"
