set output_dir [file normalize [lindex $argv 0]]
set part_name [lindex $argv 1]
set clock_period_ns [lindex $argv 2]
set root_dir [file normalize [file join [file dirname [info script]] ".."]]

file mkdir $output_dir

set module_specs {
    {iq_passthrough blocks/block_05_fpga_hdl_flow/rtl/iq_passthrough.v clk}
    {fir_iq_4tap blocks/block_05_fpga_hdl_flow/rtl/fir_iq_4tap.v clk}
    {nco_mixer_iq blocks/block_05_fpga_hdl_flow/rtl/nco_mixer_iq.v clk}
    {axis_iq_passthrough blocks/block_05_fpga_hdl_flow/rtl/axis_iq_passthrough.v aclk}
}

foreach module_spec $module_specs {
    lassign $module_spec module_name rtl_relpath clock_port

    puts "=== Running Vivado OOC synthesis for $module_name ==="
    create_project -in_memory -part $part_name

    read_verilog [file join $root_dir $rtl_relpath]

    set xdc_path [file join $output_dir "${module_name}.xdc"]
    set xdc_handle [open $xdc_path w]
    puts $xdc_handle [format {create_clock -name %s -period %.3f [get_ports %s]} $clock_port $clock_period_ns $clock_port]
    close $xdc_handle

    read_xdc $xdc_path
    synth_design -top $module_name -mode out_of_context -part $part_name

    report_utilization -file [file join $output_dir "${module_name}_utilization.rpt"]
    report_timing_summary -delay_type max -max_paths 10 -file [file join $output_dir "${module_name}_timing_summary.rpt"]
    report_clock_utilization -file [file join $output_dir "${module_name}_clock_utilization.rpt"]

    close_project
}
