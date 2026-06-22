# Course overlay CDC constraints.
#
# The PS-side AXI-Lite domain is asynchronous to the entire AD9361 receive
# clock family. Cut the relationship at the root `rx_clk` and include all
# clocks generated from it so the divided sample clocks stay covered even when
# they are materialized later in the flow.

set ctrl_async_clks [get_clocks -quiet {clk_fpga_0}]
set sample_async_clks [get_clocks -quiet -include_generated_clocks {rx_clk}]
if {[llength $ctrl_async_clks] > 0 && [llength $sample_async_clks] > 0} {
  set_clock_groups -asynchronous \
    -group $ctrl_async_clks \
    -group $sample_async_clks
}
