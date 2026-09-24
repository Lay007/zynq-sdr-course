if {[llength $argv] != 5} {
    error "usage: vivado_block8_ofdm_ooc.tcl <output_dir> <part> <clock_period_ns> <top_name> <clock_port|none>"
}

set output_dir [file normalize [lindex $argv 0]]
set part_name [lindex $argv 1]
set clock_period_ns [lindex $argv 2]
set root_dir [file normalize [file join [file dirname [info script]] ".."]]
set top_name [lindex $argv 3]
set clock_port [lindex $argv 4]

file mkdir $output_dir
set_param general.maxThreads 1
create_project -in_memory -part $part_name

# Every checked-in OFDM source; synth_design keeps only what the top uses.
foreach rtl_path [lsort [glob [file join $root_dir blocks/block_08_modulation_and_synchronization/rtl/ofdm_*.v]]] {
    read_verilog $rtl_path
}

if {$clock_port ne "none"} {
    set xdc_path [file join $output_dir "${top_name}.xdc"]
    set xdc_handle [open $xdc_path w]
    puts $xdc_handle [format {create_clock -name clk -period %.3f [get_ports %s]} $clock_period_ns $clock_port]
    puts $xdc_handle [format {set_property HD.CLK_SRC BUFGCTRL_X0Y0 [get_ports %s]} $clock_port]
    close $xdc_handle
    read_xdc $xdc_path
}

synth_design \
    -top $top_name \
    -mode out_of_context \
    -part $part_name \
    -flatten_hierarchy rebuilt

report_utilization \
    -file [file join $output_dir "${top_name}_post_synthesis_utilization.rpt"]
report_timing_summary \
    -delay_type max \
    -max_paths 10 \
    -file [file join $output_dir "${top_name}_post_synthesis_timing_summary.rpt"]

opt_design
place_design
phys_opt_design
route_design

report_utilization \
    -file [file join $output_dir "${top_name}_post_route_utilization.rpt"]
report_timing_summary \
    -delay_type max \
    -max_paths 10 \
    -file [file join $output_dir "${top_name}_post_route_timing_summary.rpt"]
report_route_status \
    -file [file join $output_dir "${top_name}_post_route_status.rpt"]
report_drc \
    -file [file join $output_dir "${top_name}_post_route_drc.rpt"]

close_project
