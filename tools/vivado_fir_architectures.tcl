# Run from an isolated build directory. All modes use the same top and XDC.
if {[llength $argv] != 1} { error "Pass one output directory" }
set out [file normalize [lindex $argv 0]]
set root [file normalize [file join [file dirname [info script]] ..]]
set part xc7z020clg400-2
file mkdir $out
set_param general.maxThreads 4

foreach {mode name} {0 parallel 1 folded 2 pipelined} {
    create_project -in_memory -part $part
    read_verilog -sv [file join $root blocks block_05_fpga_hdl_flow rtl fir_iq_architectures.sv]
    read_xdc [file join $root tools fir_architectures_ooc.xdc]
    synth_design -top fir_iq_architectures -part $part -mode out_of_context -generic ARCH=$mode
    opt_design
    place_design
    route_design
    report_utilization -file [file join $out ${name}_utilization.rpt]
    report_timing_summary -delay_type min_max -file [file join $out ${name}_timing.rpt]
    report_route_status -file [file join $out ${name}_route.rpt]
    close_project
}
