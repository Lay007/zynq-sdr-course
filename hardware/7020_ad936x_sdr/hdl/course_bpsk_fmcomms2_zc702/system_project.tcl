set script_dir [file normalize [file dirname [info script]]]
set repo_root [file normalize [file join $script_dir "../../../.."]]
set vendor_dir [file normalize [file join $script_dir "../adi_fmcomms2_reference"]]

source [file join $vendor_dir "projects/scripts/adi_env.tcl"]
source [file join $vendor_dir "projects/scripts/adi_board.tcl"]
source [file join $vendor_dir "projects/scripts/adi_project_xilinx.tcl"]

set required_vivado_version "2021.1"
if {[string compare [version -short] $required_vivado_version] != 0} {
  puts "ERROR: vivado version mismatch; expected $required_vivado_version, got [version -short]."
  puts "Set ADI_IGNORE_VERSION_CHECK=1 only if you intentionally accept the mismatch."
  exit 2
}

set project_name "course_bpsk_fmcomms2_zc702"
set project_root [file normalize [file join $script_dir "build"]]
set project_system_dir [file join $project_root "${project_name}.srcs/sources_1/bd/system"]
set xpr_path [file join $project_root "${project_name}.xpr"]

set frame_mem [file normalize [file join $repo_root "blocks/block_05_fpga_hdl_flow/rtl/bpsk_frame_bits.mem"]]
set coef_mem [file normalize [file join $repo_root "blocks/block_05_fpga_hdl_flow/rtl/bpsk_rrc_tx_fir_taps.mem"]]
foreach required_file [list $frame_mem $coef_mem] {
  if {![file exists $required_file]} {
    puts "ERROR: missing generated memory file: $required_file"
    puts "Run the Block 5 vector generators first:"
    puts "  python blocks/block_05_fpga_hdl_flow/python/generate_bpsk_rrc_tx_fir_vectors.py"
    puts "  python blocks/block_05_fpga_hdl_flow/python/generate_bpsk_framed_loopback_vectors.py"
    exit 2
  }
}

file mkdir $project_root
create_project $project_name $project_root -part xc7z020clg484-1 -force

set board_part [lindex [lsearch -all -inline [get_board_parts] *zc702*] end]
if {$board_part ne ""} {
  set_property board_part $board_part [current_project]
}

set lib_dirs $ad_hdl_dir/library
if {$ad_hdl_dir ne $ad_ghdl_dir} {
  lappend lib_dirs $ad_ghdl_dir/library
}
set_property ip_repo_paths $lib_dirs [current_fileset]
update_ip_catalog

if {![info exists ::env(ADI_DISABLE_MESSAGE_SUPPRESION)]} {
  source [file join $vendor_dir "projects/scripts/adi_xilinx_msg.tcl"]
}
set_param messaging.defaultLimit 2000

set block5_rtl_dir [file normalize [file join $repo_root "blocks/block_05_fpga_hdl_flow/rtl"]]
set block5_rtl_files [lsort [concat \
  [glob -nocomplain [file join $block5_rtl_dir "*.v"]] \
  [glob -nocomplain [file join $block5_rtl_dir "*.mem"]]]]

foreach src [concat \
  $block5_rtl_files \
  [list \
    [file join $script_dir "bpsk_zynq_ber_gpreg_bridge.v"] \
    [file join $script_dir "system_top.v"]]] {
  add_files -norecurse -fileset sources_1 $src
}
add_files -norecurse -fileset constrs_1 [file join $script_dir "system_constr.xdc"]

create_bd_design "system"
source [file join $script_dir "system_bd.tcl"]

save_bd_design
validate_bd_design
set_property synth_checkpoint_mode Hierarchical [get_files "$project_system_dir/system.bd"]
generate_target {synthesis implementation} [get_files "$project_system_dir/system.bd"]
export_ip_user_files -of_objects [get_files "$project_system_dir/system.bd"] -no_script -sync -force -quiet
create_ip_run [get_files "$project_system_dir/system.bd"]
make_wrapper -files [get_files "$project_system_dir/system.bd"] -top
import_files -force -norecurse -fileset sources_1 [file join $project_system_dir "hdl/system_wrapper.v"]

set_property top system_top [current_fileset]
update_compile_order -fileset sources_1

puts "Project created at: $project_root"
puts "Next build step:"
puts "  open_project $xpr_path"
puts "  launch_runs impl_1 -to_step write_bitstream"
