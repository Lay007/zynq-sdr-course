# Timing-closure robustness across placement strategies (Vivado 2021.1).
#
#   /g/Xilinx/Vivado/2021.1/bin/vivado.bat -mode batch -notrace -source tools/timing_directive_sweep.tcl
#
# Vivado 2021.1 has no numeric placement seed (place_design has no -seed, and the run has no
# STEPS.PLACE_DESIGN.ARGS.SEED property), so this sweeps STEPS.PLACE_DESIGN.ARGS.DIRECTIVE --
# a stronger robustness test than a seed, since it swaps the placement algorithm outright
# rather than perturbing one. It answers: is the shipped timing closure a property of the
# design, or of one lucky placement?
#
# synth_1 is reused (the RTL is unchanged), so only implementation re-runs, to route, per
# directive. STATS.WNS/TNS are the design worst/total negative slack; on this overlay they are
# faithful because the Costas multicycle-path covers both divide-select clock branches (the
# phantom clk_div_sel_1_s no longer dominates the design summary).
#
# It OVERWRITES impl_1 with the last directive's placement -- convert/keep the shipped bitstream
# first, and re-run the normal build to restore the shipped placement afterward.
#
# Configure the project path if your checkout differs.

set xpr {g:/Programs/zynq-sdr-course/tmp/vendor_xpr_course_overlay/zc702/zc702.xpr}
if {![file exists $xpr]} {
    error "project not found: $xpr -- run the normal overlay build first"
}
open_project $xpr
if {[get_property PROGRESS [get_runs synth_1]] != "100%"} {
    error "synth_1 is not complete -- run the normal build so this can reuse it"
}

# Valid 7-series single-SLR place directives that place quite differently. Explore is the one
# the course overlay ships with.
set directives {Default Explore WLDrivenBlockPlacement ExtraNetDelay_high ExtraPostPlacementOpt}
set results {}

foreach dir $directives {
    puts "==== DIRECTIVE $dir : place + route ===="
    reset_run impl_1
    set_property STEPS.PLACE_DESIGN.ARGS.DIRECTIVE $dir [get_runs impl_1]
    if {[catch { launch_runs impl_1 -to_step route_design -jobs 4 ; wait_on_run impl_1 } e]} {
        puts "DIRECTIVE $dir : LAUNCH ERROR $e" ; lappend results [list $dir ERR ERR ERR] ; continue
    }
    if {[get_property PROGRESS [get_runs impl_1]] != "100%"} {
        puts "DIRECTIVE $dir : IMPL FAILED" ; lappend results [list $dir FAILED FAILED FAILED] ; continue
    }
    set wns [get_property STATS.WNS [get_runs impl_1]]
    set tns [get_property STATS.TNS [get_runs impl_1]]
    set whs [get_property STATS.WHS [get_runs impl_1]]
    puts "DIRECTIVE $dir : WNS=$wns TNS=$tns WHS=$whs"
    lappend results [list $dir $wns $tns $whs]
}

puts "\n==================== TIMING DIRECTIVE SWEEP ===================="
puts [format "%-24s %-10s %-12s %-10s" directive WNS(ns) TNS(ns) WHS(ns)]
set min_wns 1e9
set any_fail 0
foreach r $results {
    lassign $r dir wns tns whs
    puts [format "%-24s %-10s %-12s %-10s" $dir $wns $tns $whs]
    if {$wns eq "FAILED" || $wns eq "ERR"} { set any_fail 1 ; continue }
    if {$wns < $min_wns} { set min_wns $wns }
}
puts "---------------------------------------------------------------"
if {$any_fail} {
    puts "INCOMPLETE: at least one directive did not finish -- see log"
} elseif {$min_wns >= 0} {
    puts "ROBUST: every placement strategy met timing (worst WNS across directives = $min_wns ns)"
} else {
    puts "MARGINAL: at least one strategy missed timing (worst WNS = $min_wns ns) -- needs margin work"
}
puts "DIRECTIVE SWEEP DONE"
