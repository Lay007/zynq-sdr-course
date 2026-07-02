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

# The Gardner symbol timing-recovery loop (bpsk_symbol_timing_recovery) updates its
# NCO / loop-filter / interpolator state once per ADC capture-valid. capture_in_valid
# is the AD9361 sample strobe (~3.84 MHz) seen inside the ~62.5 MHz sample clock, so
# those state registers only change roughly every 16 sample-clock cycles. Their
# recurrence (nco -> interpolate -> sign-Gardner TED -> PI loop -> w_step) is a long
# combinational path that cannot close in a single 16 ns period, so relax the DATA
# inputs (D pins only, not the clock enable) by a multicycle. Setup 2 (32 ns) covers
# the ~21.5 ns path with margin and is safe because the enable is >= ~15 cycles sparse.
set tr_cells [get_cells -hier -quiet -filter {NAME =~ *g_timing_recovery.timing_i/*}]
if {[llength $tr_cells] > 0} {
  # Relax the data-carrying input pins (D and the sync set/reset R/S, which the
  # tools may use for the clamp / W_NOMINAL constants) but NOT the clock enable CE:
  # CE is the per-cycle capture_in_valid strobe and must stay single-cycle.
  set tr_d [get_pins -quiet -of_objects $tr_cells \
              -filter {REF_PIN_NAME == D || REF_PIN_NAME == R || REF_PIN_NAME == S}]
  if {[llength $tr_d] > 0} {
    # util_ad9361_divclk exposes two run-time divide-select clocks on the sample
    # clock (62.5 MHz and 125 MHz); only one is active but the tools analyze both.
    # Setup 4 covers the ~21.5 ns recurrence on the faster 8 ns clock (32 ns) and on
    # the 16 ns clock (64 ns); both are safe because capture_in_valid is >= ~16/32
    # cycles sparse.
    set_multicycle_path -setup 4 -to $tr_d
    set_multicycle_path -hold  3 -to $tr_d
    puts "course overlay: multicycle-path (setup 4) applied to [llength $tr_d] timing-recovery data pins"
  }
}

# bridge_rx_lclk_fifo (raw-ADC RX CDC FIFO) gray-code pointer crossings. wr_clk is
# l_clk (rx_clk) and rd_clk is the divided sample clock (generated from rx_clk), so
# the two are RELATED and the async clock-group cut above does not cover them; the
# tool then times the gray pointer -> 2-flop synchronizer capture as a real 4 ns
# rx_clk path and fails setup (~ -0.78 ns, placement-dependent). A gray-coded
# pointer through a 2-flop ASYNC_REG synchronizer is a safe CDC (at most one bit
# changes per step), so false-path the capture into the first synchronizer flop —
# the standard async-FIFO constraint.
set fifo_cdc [get_pins -hier -quiet -filter { \
    NAME =~ *rx_raw_fifo_i/rgray_wr1_reg*/D || NAME =~ *rx_raw_fifo_i/wgray_rd1_reg*/D}]
if {[llength $fifo_cdc] > 0} {
  set_false_path -to $fifo_cdc
  puts "course overlay: false_path applied to [llength $fifo_cdc] rx_raw_fifo CDC sync pins"
}
