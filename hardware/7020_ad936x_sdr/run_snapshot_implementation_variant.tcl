# Implement one placement/routing variant from the complete post-opt vendor
# snapshot checkpoint. Arguments:
#   run_name place_directive phys_directive route_directive tns_cleanup post_route_phys

if {[llength $argv] != 6} {
  error "Expected: run_name place_directive phys_directive route_directive tns_cleanup post_route_phys"
}
lassign $argv run_name place_directive phys_directive route_directive tns_cleanup post_route_phys

set script_dir [file dirname [file normalize [info script]]]
set repo_root [file normalize [file join $script_dir "../.."]]
set source_checkpoint [file join $repo_root "tmp/vendor_xpr_course_overlay/zc702/zc702.runs/impl_1/system_top_opt.dcp"]
set timing_xdc [file join $script_dir "hdl/course_bpsk_fmcomms2_zc702/course_overlay_timing.xdc"]
set output_dir [file join $repo_root "tmp/snapshot_impl_sweep/$run_name"]

if {![file exists $source_checkpoint]} {
  error "Missing complete post-opt checkpoint: $source_checkpoint"
}
if {![file exists $timing_xdc]} {
  error "Missing overlay timing constraints: $timing_xdc"
}
if {$tns_cleanup ne "0" && $tns_cleanup ne "1"} {
  error "tns_cleanup must be 0 or 1"
}

file mkdir $output_dir
cd $output_dir
puts "COURSE_VARIANT_RUN=$run_name"
puts "COURSE_VARIANT_PLACE=$place_directive"
puts "COURSE_VARIANT_PHYS=$phys_directive"
puts "COURSE_VARIANT_ROUTE=$route_directive"
puts "COURSE_VARIANT_TNS_CLEANUP=$tns_cleanup"
puts "COURSE_VARIANT_POST_ROUTE_PHYS=$post_route_phys"

open_checkpoint $source_checkpoint
source $timing_xdc

place_design -directive $place_directive
report_utilization -file system_top_utilization_placed.rpt
write_checkpoint -force system_top_placed.dcp

phys_opt_design -directive $phys_directive
write_checkpoint -force system_top_physopt.dcp

if {$tns_cleanup eq "1"} {
  route_design -directive $route_directive -tns_cleanup
} else {
  route_design -directive $route_directive
}
if {$post_route_phys ne "none"} {
  phys_opt_design -directive $post_route_phys
}

report_timing_summary -file system_top_timing_summary_routed.rpt
report_clock_utilization -file system_top_clock_utilization_routed.rpt
report_route_status -file system_top_route_status.rpt
write_checkpoint -force system_top_routed.dcp
write_bitstream -force system_top.bit

puts "COURSE_VARIANT_DONE=$run_name"
exit
