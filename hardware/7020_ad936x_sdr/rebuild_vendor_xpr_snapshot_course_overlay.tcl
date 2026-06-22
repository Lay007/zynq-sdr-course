# Rebuild the surviving vendor zc702.xpr snapshot from a disposable workspace,
# patch the PS7 MIO14/15 directions, and then graft the course overlay onto
# that boot-safe editable baseline.
#
# This flow is the next gated bring-up step after the pure-Tcl recreated
# vendor shell proved structurally close but still not boot-safe on hardware.

set script_dir [file normalize [file dirname [info script]]]
set bundle_root [file normalize $script_dir]
set repo_root [file normalize [file join $bundle_root ".." ".."]]
set course_hdl_dir [file join $bundle_root "hdl" "course_bpsk_fmcomms2_zc702"]
set vendor_dir [file join $bundle_root "hdl" "adi_fmcomms2_reference"]
set source_project_dir [file join $vendor_dir "projects" "fmcomms2" "zc702"]
set adi_scripts_dir [file join $vendor_dir "projects" "scripts"]
set axi_gpreg_dir [file join $vendor_dir "library" "axi_gpreg"]
set block5_rtl_dir [file join $repo_root "blocks" "block_05_fpga_hdl_flow" "rtl"]
set work_root [file normalize [file join $repo_root "tmp" "vendor_xpr_course_overlay"]]
set work_project_dir [file join $work_root "zc702"]
set work_xpr_path [file join $work_project_dir "zc702.xpr"]
set work_bd_path [file join \
  $work_project_dir "zc702.srcs" "sources_1" "bd" "system" "system.bd"]
set work_bd_dir [file dirname $work_bd_path]
set work_wrapper_path [file join $work_bd_dir "hdl" "system_wrapper.v"]
set work_xsa_path [file join $work_project_dir "zc702.sdk" "system_top.xsa"]
set overlay_helper [file join $course_hdl_dir "course_overlay_injection.tcl"]
set overlay_timing_xdc [file join $course_hdl_dir "course_overlay_timing.xdc"]

proc env_truthy {name} {
  if {![info exists ::env($name)]} {
    return 0
  }
  set value [string tolower $::env($name)]
  return [expr {$value eq "1" || $value eq "true" || $value eq "yes" || $value eq "on"}]
}

proc ensure_under {child parent label} {
  set child_norm [file normalize $child]
  set parent_norm [file normalize $parent]
  if {[string first $parent_norm $child_norm] != 0} {
    error "$label is outside the expected parent: $child_norm vs $parent_norm"
  }
}

proc ensure_path_exists {path label} {
  if {![file exists $path]} {
    error "Missing $label: $path"
  }
}

proc seed_snapshot_project_copy {source_project_dir work_project_dir} {
  file mkdir $work_project_dir
  foreach item {zc702.xpr zc702.srcs} {
    set source_path [file join $source_project_dir $item]
    ensure_path_exists $source_path "snapshot seed item"
    file copy -force $source_path [file join $work_project_dir $item]
  }
}

proc package_axi_gpreg_if_needed {axi_gpreg_dir} {
  set component_xml [file join $axi_gpreg_dir "component.xml"]
  if {[file exists $component_xml]} {
    return
  }
  puts "Packaging missing axi_gpreg IP in $axi_gpreg_dir"
  set original_dir [pwd]
  cd $axi_gpreg_dir
  source axi_gpreg_ip.tcl
  close_project
  cd $original_dir
}

proc configure_project_ip_catalog {vendor_dir} {
  set lib_dirs $::ad_hdl_dir/library
  if {$::ad_hdl_dir ne $::ad_ghdl_dir} {
    lappend lib_dirs $::ad_ghdl_dir/library
  }
  set_property ip_repo_paths $lib_dirs [current_fileset]
  update_ip_catalog

  if {![info exists ::env(ADI_DISABLE_MESSAGE_SUPPRESION)]} {
    source [file join $vendor_dir "projects" "scripts" "adi_xilinx_msg.tcl"]
  }
  set_param messaging.defaultLimit 2000
}

proc collect_bridge_overlay_sources {course_hdl_dir block5_rtl_dir} {
  set frame_mem [file normalize [file join $block5_rtl_dir "bpsk_frame_bits.mem"]]
  set coef_mem [file normalize [file join $block5_rtl_dir "bpsk_rrc_tx_fir_taps.mem"]]
  foreach required_file [list $frame_mem $coef_mem] {
    if {![file exists $required_file]} {
      error "Missing generated memory file for bridge_rx_only mode: $required_file"
    }
  }

  set block5_rtl_files [lsort [concat \
    [glob -nocomplain [file join $block5_rtl_dir "*.v"]] \
    [glob -nocomplain [file join $block5_rtl_dir "*.mem"]]]]

  return [concat \
    $block5_rtl_files \
    [list \
      [file join $course_hdl_dir "course_dac_fifo_source_mux.v"] \
      [file join $course_hdl_dir "bpsk_zynq_ber_gpreg_bridge.v"] \
      [file join $course_hdl_dir "bpsk_zynq_ber_bridge_bd.v"]]]
}

proc add_overlay_sources {overlay_mode course_hdl_dir block5_rtl_dir} {
  if {$overlay_mode ne "bridge_rx_only" && $overlay_mode ne "bridge_txrx_mux"} {
    return
  }

  foreach src [collect_bridge_overlay_sources $course_hdl_dir $block5_rtl_dir] {
    ensure_path_exists $src "bridge overlay source"
    add_files -norecurse -fileset sources_1 $src
  }
}

proc configure_overlay_timing_hook {overlay_timing_xdc} {
  set impl_run [get_runs -quiet impl_1]
  if {$impl_run eq ""} {
    error "Missing impl_1 run while configuring overlay timing hook"
  }
  set_property STEPS.OPT_DESIGN.TCL.PRE $overlay_timing_xdc $impl_run
}

proc patch_snapshot_bd {bd_path overlay_helper overlay_mode} {
  open_bd_design $bd_path
  source $overlay_helper
  course_bpsk_apply_overlay $overlay_mode
  validate_bd_design
  save_bd_design
  close_bd_design [current_bd_design]
}

ensure_path_exists $source_project_dir "vendor snapshot project directory"
ensure_path_exists [file join $adi_scripts_dir "adi_project_xilinx.tcl"] "ADI project helper"
ensure_path_exists $overlay_helper "course overlay helper"
ensure_path_exists $overlay_timing_xdc "course overlay timing constraints"

source [file join $adi_scripts_dir "adi_env.tcl"]
source [file join $adi_scripts_dir "adi_board.tcl"]
source [file join $adi_scripts_dir "adi_project_xilinx.tcl"]

package_axi_gpreg_if_needed $axi_gpreg_dir

set overlay_mode "gpreg_only"
if {[info exists ::env(COURSE_OVERLAY_MODE)]} {
  set overlay_mode $::env(COURSE_OVERLAY_MODE)
}
set skip_run [env_truthy "COURSE_SNAPSHOT_SKIP_RUN"]

puts "Snapshot overlay mode: $overlay_mode"
puts "Skip synth/impl/export: $skip_run"

ensure_under $work_root $repo_root "Temporary work root"
if {[file exists $work_root]} {
  file delete -force $work_root
}
file mkdir $work_root
seed_snapshot_project_copy $source_project_dir $work_project_dir

set original_dir [pwd]
set run_failed [catch {
  cd $work_project_dir
  open_project $work_xpr_path
  configure_project_ip_catalog $vendor_dir
  add_overlay_sources $overlay_mode $course_hdl_dir $block5_rtl_dir
  configure_overlay_timing_hook $overlay_timing_xdc
  patch_snapshot_bd $work_bd_path $overlay_helper $overlay_mode
  generate_target all [get_files $work_bd_path]
  make_wrapper -files [get_files $work_bd_path] -top -force
  import_files -force -norecurse -fileset sources_1 $work_wrapper_path
  set_property top system_top [current_fileset]
  update_compile_order -fileset sources_1

  if {$skip_run} {
    puts "COURSE_SNAPSHOT_SKIP_RUN=1: stopping after BD regeneration and wrapper import."
  } else {
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
  }
} run_error run_options]
cd $original_dir

if {$run_failed} {
  return -options $run_options $run_error
}

if {!$skip_run && ![file exists $work_xsa_path]} {
  error "Expected rebuilt XSA was not generated: $work_xsa_path"
}

puts "Rebuilt patched snapshot overlay project at: $work_project_dir"
if {$skip_run} {
  puts "Project smoke completed without synth/impl/export."
} else {
  puts "Exported XSA: $work_xsa_path"
}
