# Run each family in an isolated directory to keep reports and ROM inputs local.
if {[llength $argv] != 2} { error "usage: <fft|nco> <output directory>" }
lassign $argv family out
set out [file normalize $out]
set root [file normalize [file join [file dirname [info script]] ..]]
set part xc7z020clg400-2
set_param general.maxThreads 4

if {$family eq "fft"} {
    set top ofdm_fft64_sequential
    set rtl [file join $root blocks block_08_modulation_and_synchronization rtl]
    set sources [list [file join $rtl ofdm_fft64_sequential.v] \
        [file join $rtl ofdm_ifft64_sequential.v] [file join $rtl ofdm_ifft_butterfly.v] \
        [file join $rtl ofdm_iq_bank_ram.v]]
    set modes {fft_base {PIPELINED=0 BRAM_MEMORY=0} fft_fabric {PIPELINED=1 BRAM_MEMORY=0} fft_bram {PIPELINED=1 BRAM_MEMORY=1}}
} elseif {$family eq "nco"} {
    set top nco_phase_architectures
    set sources [list [file join $root blocks block_05_fpga_hdl_flow rtl nco_phase_architectures.sv]]
    set modes {nco_lut {CORDIC=0} nco_cordic {CORDIC=1}}
    if {![file exists nco_quarter_q15.mem]} { error "Generate nco_quarter_q15.mem in the current directory first" }
} else {
    error "Unknown family: $family"
}

file mkdir $out
foreach {name generics} $modes {
    create_project -in_memory -part $part
    read_verilog -sv $sources
    # Identical 10 ns clock and ideal external I/O delays in every run.
    read_xdc [file join $root tools fir_architectures_ooc.xdc]
    set options {}
    foreach generic $generics { lappend options -generic $generic }
    synth_design -top $top -part $part -mode out_of_context {*}$options
    opt_design
    place_design
    route_design
    report_utilization -file [file join $out ${name}_utilization.rpt]
    report_timing_summary -delay_type min_max -file [file join $out ${name}_timing.rpt]
    report_route_status -file [file join $out ${name}_route.rpt]
    close_project
}
