if {[llength $argv] != 4} {
    error "usage: vivado_block8_css_ooc.tcl <output_dir> <part> <clock_period_ns> <top_name>"
}

set output_dir [file normalize [lindex $argv 0]]
set part_name [lindex $argv 1]
set clock_period_ns [lindex $argv 2]
set root_dir [file normalize [file join [file dirname [info script]] ".."]]
set top_name [lindex $argv 3]

set rtl_relpaths {
    blocks/block_08_modulation_and_synchronization/rtl/css_dechirp_mul.v
    blocks/block_08_modulation_and_synchronization/rtl/css_sf7_ref_rom.v
    blocks/block_08_modulation_and_synchronization/rtl/css_sf7_dechirp_frontend.v
    blocks/block_08_modulation_and_synchronization/rtl/css_q15_rom.v
    blocks/block_08_modulation_and_synchronization/rtl/css_symbol_buffer.v
    blocks/block_08_modulation_and_synchronization/rtl/css_dft128_core.v
    blocks/block_08_modulation_and_synchronization/rtl/css_peak_detector.v
    blocks/block_08_modulation_and_synchronization/rtl/css_sf7_sequential_detector.v
    blocks/block_08_modulation_and_synchronization/rtl/css_sf7_axis_detector.v
    blocks/block_08_modulation_and_synchronization/rtl/css_sf7_axi_accelerator.v
}

file mkdir $output_dir
create_project -in_memory -part $part_name

foreach rtl_relpath $rtl_relpaths {
    read_verilog [file join $root_dir $rtl_relpath]
}

set xdc_path [file join $output_dir "${top_name}.xdc"]
set xdc_handle [open $xdc_path w]
puts $xdc_handle [format {create_clock -name clk -period %.3f [get_ports clk]} $clock_period_ns]
puts $xdc_handle {set_property HD.CLK_SRC BUFGCTRL_X0Y0 [get_ports clk]}
close $xdc_handle
read_xdc $xdc_path

synth_design \
    -top $top_name \
    -mode out_of_context \
    -part $part_name \
    -flatten_hierarchy rebuilt

report_utilization \
    -file [file join $output_dir "${top_name}_post_synthesis_utilization.rpt"]
report_utilization \
    -hierarchical \
    -hierarchical_depth 4 \
    -file [file join $output_dir "${top_name}_post_synthesis_utilization_hierarchical.rpt"]
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
report_utilization \
    -hierarchical \
    -hierarchical_depth 4 \
    -file [file join $output_dir "${top_name}_post_route_utilization_hierarchical.rpt"]
report_timing_summary \
    -delay_type max \
    -max_paths 10 \
    -file [file join $output_dir "${top_name}_post_route_timing_summary.rpt"]
report_route_status \
    -file [file join $output_dir "${top_name}_post_route_status.rpt"]
report_clock_utilization \
    -file [file join $output_dir "${top_name}_post_route_clock_utilization.rpt"]
report_drc \
    -file [file join $output_dir "${top_name}_post_route_drc.rpt"]

close_project
