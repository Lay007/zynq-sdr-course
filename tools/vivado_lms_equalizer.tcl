if {[llength $argv] != 1} { error "usage: <output directory>" }
set out [file normalize [lindex $argv 0]]
set root [file normalize [file join [file dirname [info script]] ..]]
set part xc7z020clg400-2
set_param general.maxThreads 4

file mkdir $out
create_project -in_memory -part $part
read_verilog -sv [file join $root blocks block_05_fpga_hdl_flow rtl lms_equalizer_2tap.sv]
# Reuse the 10 ns clock and ideal I/O delays of the other OOC experiments.
read_xdc [file join $root tools fir_architectures_ooc.xdc]
synth_design -top lms_equalizer_2tap -part $part -mode out_of_context
opt_design
place_design
route_design
report_utilization -file [file join $out lms_utilization.rpt]
report_timing_summary -delay_type min_max -file [file join $out lms_timing.rpt]
report_route_status -file [file join $out lms_route.rpt]
close_project
