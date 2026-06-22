set script_dir [file normalize [file dirname [info script]]]
set vendor_shell_bd [file join $script_dir "vendor_system_bd_clg400.tcl"]
set overlay_helper [file join $script_dir "course_overlay_injection.tcl"]

source $vendor_shell_bd
source $overlay_helper
course_bpsk_apply_overlay [course_bpsk_overlay_mode]
