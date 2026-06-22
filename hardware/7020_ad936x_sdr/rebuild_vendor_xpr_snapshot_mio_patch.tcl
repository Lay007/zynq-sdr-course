# Rebuild the surviving vendor zc702.xpr snapshot from a disposable workspace,
# but patch the PS7 MIO14/15 directions before synthesis/implementation.
#
# This flow exists because the checked-in snapshot is the closest surviving
# editable witness to the clean-boot vendor reference XSA, while the pure-Tcl
# recreation still drifts at derived/read-only parameters.

set script_dir [file normalize [file dirname [info script]]]
set bundle_root [file normalize $script_dir]
set repo_root [file normalize [file join $bundle_root ".." ".."]]

set source_project_dir [file join \
  $bundle_root "hdl" "adi_fmcomms2_reference" "projects" "fmcomms2" "zc702"]
set adi_scripts_dir [file join \
  $bundle_root "hdl" "adi_fmcomms2_reference" "projects" "scripts"]
set work_root [file normalize [file join $repo_root "tmp" "vendor_xpr_mio14_15_patch"]]
set work_project_dir [file join $work_root "zc702"]
set work_xpr_path [file join $work_project_dir "zc702.xpr"]
set work_bd_path [file join \
  $work_project_dir "zc702.srcs" "sources_1" "bd" "system" "system.bd"]
set work_xsa_path [file join $work_project_dir "zc702.sdk" "system_top.xsa"]

proc ensure_under {child parent label} {
  set child_norm [file normalize $child]
  set parent_norm [file normalize $parent]
  if {[string first $parent_norm $child_norm] != 0} {
    error "$label is outside the expected parent: $child_norm vs $parent_norm"
  }
}

proc patch_sys_ps7_mio_directions {bd_path} {
  open_bd_design $bd_path
  set ps7_cell [get_bd_cells sys_ps7]
  if {[llength $ps7_cell] == 0} {
    error "Missing sys_ps7 in $bd_path"
  }
  set_property -dict [list \
    CONFIG.preset {None} \
    CONFIG.PCW_MIO_14_DIRECTION {in} \
    CONFIG.PCW_MIO_15_DIRECTION {out} \
  ] $ps7_cell
  validate_bd_design
  save_bd_design
  close_bd_design [current_bd_design]
}

if {![file exists $source_project_dir]} {
  error "Missing source project directory: $source_project_dir"
}

if {![file exists [file join $adi_scripts_dir "adi_project_xilinx.tcl"]]} {
  error "Missing ADI build helper scripts under: $adi_scripts_dir"
}

ensure_under $work_root $repo_root "Temporary work root"
if {[file exists $work_root]} {
  file delete -force $work_root
}
file mkdir $work_root
file copy $source_project_dir $work_project_dir

source [file join $adi_scripts_dir "adi_env.tcl"]
source [file join $adi_scripts_dir "adi_project_xilinx.tcl"]

set original_dir [pwd]
set run_failed [catch {
  cd $work_project_dir
  open_project $work_xpr_path
  patch_sys_ps7_mio_directions $work_bd_path
  generate_target all [get_files $work_bd_path]
  make_wrapper -files [get_files $work_bd_path] -top -force
  update_compile_order -fileset sources_1

  set runs_to_reset {}
  foreach pattern {impl_1 synth_1 system_*_synth_1} {
    foreach run_obj [get_runs -quiet $pattern] {
      lappend runs_to_reset $run_obj
    }
  }
  if {[llength $runs_to_reset] != 0} {
    reset_run $runs_to_reset
  }

  adi_project_run zc702
} run_error run_options]
cd $original_dir

if {$run_failed} {
  return -options $run_options $run_error
}

if {![file exists $work_xsa_path]} {
  error "Expected rebuilt XSA was not generated: $work_xsa_path"
}

puts "Rebuilt patched snapshot project at: $work_project_dir"
puts "Exported XSA: $work_xsa_path"
