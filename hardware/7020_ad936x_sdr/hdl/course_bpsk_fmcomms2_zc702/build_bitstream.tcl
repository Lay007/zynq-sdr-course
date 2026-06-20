set script_dir [file normalize [file dirname [info script]]]
set vendor_dir [file normalize [file join $script_dir "../adi_fmcomms2_reference"]]
set project_name "course_bpsk_fmcomms2_zc702"
set xpr_path [file normalize [file join $script_dir "build" "${project_name}.xpr"]]

if {![file exists $xpr_path]} {
  puts "ERROR: missing Vivado project: $xpr_path"
  puts "Run system_project.tcl first."
  exit 2
}

# Match the project creation flow: build the course overlay in-project instead
# of reusing OOC checkpoints from the shared ADI cache.
set ADI_USE_OOC_SYNTHESIS 0
set ADI_USE_INCR_COMP 0

source [file join $vendor_dir "projects/scripts/adi_env.tcl"]
source [file join $vendor_dir "projects/scripts/adi_project_xilinx.tcl"]

# Keep the ADI helper outputs (`timing_*.log`, `*.sdk/system_top.xsa`) next to
# this script instead of leaking them into the caller's working directory.
set original_dir [pwd]
set run_failed [catch {
  cd $script_dir
  open_project $xpr_path
  if {[llength [get_runs -quiet impl_1]] != 0} {
    reset_run impl_1
  }
  if {[llength [get_runs -quiet synth_1]] != 0} {
    reset_run synth_1
  }
  adi_project_run $project_name
} run_error run_options]
cd $original_dir
if {$run_failed} {
  return -options $run_options $run_error
}

puts "Implementation finished for $project_name"
puts "Bitstream/XSA directory: [file join $script_dir "${project_name}.sdk"]"
