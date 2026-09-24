# Lab 5.12: build the PS/PL mailbox Block Design end to end.
#
# usage: vivado -mode batch -source vivado_block5_mailbox_bd.tcl
#          -tclargs <build_dir> <ps7_params.tcl> <report_dir>
#
# <ps7_params.tcl> defines `ps7_board_params` (a flat name/value list of the
# board's PCW_* settings, extracted from its known-good XSA by
# tools/build_block5_mailbox_bd.py). The flow follows the procedure in
# lab_5_12_zynq_ps_pl_mailbox_en.md.

if {[llength $argv] != 3} {
    error "usage: vivado_block5_mailbox_bd.tcl <build_dir> <ps7_params.tcl> <report_dir>"
}
set build_dir [file normalize [lindex $argv 0]]
set params_file [file normalize [lindex $argv 1]]
set report_dir [file normalize [lindex $argv 2]]
set root_dir [file normalize [file join [file dirname [info script]] ".."]]
file mkdir $report_dir

set_param general.maxThreads 1
# The project gets its own subdirectory: create_project -force empties its target,
# and $build_dir is Vivado's working directory and holds the PS7 parameter file.
set proj_dir [file join $build_dir proj]
create_project mailbox_echo $proj_dir -part xc7z020clg400-2 -force
add_files [list \
    [file join $root_dir blocks/block_05_fpga_hdl_flow/rtl/zynq_message_mailbox_axi_lite.v] \
    [file join $root_dir blocks/block_05_fpga_hdl_flow/rtl/zynq_message_mailbox_vivado_wrapper.v]]
update_compile_order -fileset sources_1

# 1. New BD.
create_bd_design "mailbox_echo_bd"

# 2. Zynq PS with the board's own DDR/MIO/peripheral settings. No board part is
#    set, so block automation must not apply a board preset.
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
# The lab needs one AXI master, one PL clock and its reset on top of the board setup.
set_property -dict [list \
    CONFIG.PCW_USE_M_AXI_GP0 {1} \
    CONFIG.PCW_EN_CLK0_PORT {1} \
    CONFIG.PCW_EN_RST0_PORT {1} \
    CONFIG.PCW_FPGA0_PERIPHERAL_FREQMHZ {100}] $ps

# 3. The mailbox as a module reference (the same wrapper iverilog elaborates in CI).
create_bd_cell -type module -reference zynq_message_mailbox_vivado_wrapper mailbox_0

# 4. M_AXI_GP0 -> interconnect -> mailbox S_AXI, clock and reset by automation.
apply_bd_automation -rule xilinx.com:bd_rule:axi4 \
    -config {Master "/processing_system7_0/M_AXI_GP0" Clk "Auto"} \
    [get_bd_intf_pins mailbox_0/S_AXI]

# 5-6. Let Vivado assign the address, then validate.
assign_bd_address
# Step 6 of the lab recipe: a 4K window covers the 0x00-0xAC register map. Without it
# Vivado gives the module reference the whole 1 GB M_AXI_GP0 window.
set_property range 4K [get_bd_addr_segs {processing_system7_0/Data/SEG_mailbox_0_reg0}]
validate_bd_design
save_bd_design

set seg [get_bd_addr_segs -of_objects [get_bd_addr_spaces processing_system7_0/Data]]
set seg_offset [get_property OFFSET $seg]
set seg_range [get_property RANGE $seg]
set fclk0 [get_property CONFIG.PCW_FPGA0_PERIPHERAL_FREQMHZ $ps]
set fclk0_actual [get_property CONFIG.PCW_ACT_FPGA0_PERIPHERAL_FREQMHZ $ps]

# 7. Wrapper, synthesis, implementation, bitstream, XSA.
set bd_file [get_files mailbox_echo_bd.bd]
make_wrapper -files $bd_file -top
add_files -norecurse [file join $proj_dir mailbox_echo.gen sources_1 bd mailbox_echo_bd hdl mailbox_echo_bd_wrapper.v]
set_property top mailbox_echo_bd_wrapper [current_fileset]
update_compile_order -fileset sources_1

# One job at a time: on a 16 GB machine four parallel IP syntheses ran out of memory.
launch_runs impl_1 -to_step write_bitstream -jobs 1
wait_on_run impl_1
if {[get_property PROGRESS [get_runs impl_1]] ne "100%"} {
    error "implementation did not complete: [get_property STATUS [get_runs impl_1]]"
}
open_run impl_1
report_utilization -file [file join $report_dir mailbox_echo_utilization.rpt]
report_utilization -hierarchical -hierarchical_depth 3 -file [file join $report_dir mailbox_echo_utilization_hierarchical.rpt]
report_timing_summary -delay_type max -max_paths 5 -file [file join $report_dir mailbox_echo_timing_summary.rpt]
report_drc -file [file join $report_dir mailbox_echo_drc.rpt]
write_hw_platform -fixed -include_bit -force -file [file join $build_dir mailbox_echo_bd_wrapper.xsa]

set out [open [file join $report_dir mailbox_echo_build.json] w]
puts $out "{"
puts $out "  \"segment\": \"[get_property NAME $seg]\","
puts $out "  \"offset\": \"$seg_offset\","
puts $out "  \"range\": \"$seg_range\","
puts $out "  \"fclk0_requested_mhz\": \"$fclk0\","
puts $out "  \"fclk0_actual_mhz\": \"$fclk0_actual\","
puts $out "  \"ps7_params_written\": $applied,"
puts $out "  \"ps7_params_write_errors\": [llength $skipped],"
puts $out "  \"bitstream\": \"[file tail [get_property DIRECTORY [get_runs impl_1]]]/mailbox_echo_bd_wrapper.bit\","
puts $out "  \"vivado\": \"[version -short]\""
puts $out "}"
close $out
set skip_out [open [file join $report_dir mailbox_echo_ps7_skipped_params.txt] w]
puts $skip_out [join $skipped "\n"]
close $skip_out
puts "MAILBOX_SEGMENT [get_property NAME $seg] OFFSET $seg_offset RANGE $seg_range"
