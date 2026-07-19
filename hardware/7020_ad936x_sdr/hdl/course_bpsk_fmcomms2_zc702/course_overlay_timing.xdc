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

# The QPSK Costas loop (qpsk_costas) updates theta / freq once per RECOVERED SYMBOL, and
# the symbol sampler emits one symbol every SPS=8 sample-clock cycles. Its recurrence
# (NCO phase -> cos/sin LUT -> complex de-rotate -> decision-directed PED -> PI -> phase)
# is ~16 ns of logic (23 levels, 2 DSP48), so it does not close in one 16 ns sample-clock
# period (measured -0.057 ns), and it fails outright against the 8 ns divide-select clock
# the tools also analyze. Relax the DATA pins (D, and the sync set/reset R/S the tools may
# use for the LUT constants) but NOT the clock enable CE, which carries the per-symbol
# strobe and must stay single-cycle. Setup 4 covers the path on both the 16 ns and the
# 8 ns clock, and is safe because updates are >= 8 cycles apart.
set costas_cells [get_cells -hier -quiet -filter {NAME =~ *costas_i/*}]
if {[llength $costas_cells] > 0} {
  # D/R/S catches fabric FFs; A*/B*/C* catches DSP48 data inputs (e.g. the input de-rotate multiply
  # y_q0/A that a coarse->Costas per-symbol path lands on), which REF_PIN_NAME == D does not.
  set costas_d [get_pins -quiet -of_objects $costas_cells \
                  -filter {REF_PIN_NAME == D || REF_PIN_NAME == R || REF_PIN_NAME == S || \
                           REF_PIN_NAME =~ A* || REF_PIN_NAME =~ B* || REF_PIN_NAME =~ C*}]
  if {[llength $costas_d] > 0} {
    set_multicycle_path -setup 4 -to $costas_d
    set_multicycle_path -hold  3 -to $costas_d
    puts "course overlay: multicycle-path (setup 4) applied to [llength $costas_d] Costas data pins"
  }
}

# The coarse-CFO estimator (qpsk_coarse_cfo) has two once-per-symbol datapaths that cannot close in
# one sample-clock period, at the SAME cadence the Costas loop above runs at (updates on in_valid):
#   * acc_i/acc_q -- the differential 4th-power accumulate: a complex multiply feeding a 48-bit add
#     (measured 21.8 ns, 21 logic levels incl. DSP48 + a 12-deep CARRY4 chain);
#   * out_i_r/out_q_r -- the registered derotate output: theta -> Q15 cos/sin LUT -> complex
#     multiply -> >>>15, captured on in_valid (the register exists precisely so this long path does
#     NOT reach the downstream Costas per-symbol enable gate as a single-cycle cross-module path).
# Both fail outright (down to -13.9 ns) against the 8 ns divide-select clock the tools also analyze.
# Relax ONLY these accumulator/output data pins. Crucially this must NOT be the whole coarse block:
# the CORDIC state (cx/cy/cang/citer) iterates EVERY cycle during the once-per-window rotation and
# must stay single-cycle (it already meets timing). The `-to <reg>/D` covers each entire path through
# its DSP/LUT regardless of launch register, and leaves the clock enable (the per-symbol strobe)
# single-cycle. Setup 4 covers the paths on both the 16 ns (64 ns) and 8 ns (32 ns) clocks; safe
# because these registers update >= 8 cycles apart.
# Match by prefix, NOT *_reg exactly: the 48-bit accumulate is mapped through intermediate
# synthesis registers (e.g. acc_i[19]_i_10_psdsp_1) that carry the same per-symbol data but are
# not named acc_i_reg, so a *_reg-only filter leaves them single-cycle and they fail. acc_i* /
# acc_q* catch those. The explicit include-list (accumulate, registered output, previous-y4, and
# the derotate phase) is every coarse register whose inputs are stable between in_valid pulses; the
# CORDIC state (cx/cy/cang/citer/cfold), the FSM state, and omega are deliberately EXCLUDED because
# they capture from the per-cycle CORDIC and must stay single-cycle.
set coarse_slow [get_cells -hier -quiet -filter {NAME =~ *coarse_cfo_i/acc_i* || \
                                                 NAME =~ *coarse_cfo_i/acc_q* || \
                                                 NAME =~ *coarse_cfo_i/p_i_r* || \
                                                 NAME =~ *coarse_cfo_i/p_q_r* || \
                                                 NAME =~ *coarse_cfo_i/out_i_r* || \
                                                 NAME =~ *coarse_cfo_i/out_q_r* || \
                                                 NAME =~ *coarse_cfo_i/y4p_i* || \
                                                 NAME =~ *coarse_cfo_i/y4p_q* || \
                                                 NAME =~ *coarse_cfo_i/theta_reg*}]
if {[llength $coarse_slow] > 0} {
  set coarse_d [get_pins -quiet -of_objects $coarse_slow \
                  -filter {REF_PIN_NAME == D || REF_PIN_NAME == R || REF_PIN_NAME == S || \
                           REF_PIN_NAME =~ A* || REF_PIN_NAME =~ B* || REF_PIN_NAME =~ C*}]
  if {[llength $coarse_d] > 0} {
    set_multicycle_path -setup 4 -to $coarse_d
    set_multicycle_path -hold  3 -to $coarse_d
    puts "course overlay: multicycle-path (setup 4) applied to [llength $coarse_d] coarse-CFO accumulator/output data pins"
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

# Same FIFO, the read DATA path: the distributed-RAM cell is written on rx_clk (4 ns) and read into
# rd_i/rd_q on the divided sample clock; being related clocks, the tool times it as a tight 4 ns
# crossing (-0.7 ns, 86% route, placement-dependent -- it only slipped once the coarse-CFO logic
# crowded the region; the stock build met it by ~+0.02 ns, i.e. luck). The gray read pointer
# (synchronized through two flops, false-pathed above) guarantees the word has been sitting in
# memory for at least two read cycles before it is selected, so the exact rx_clk edge is a false
# relationship. Bound it datapath-only to one read period instead of removing it entirely, which
# still catches gross bit-to-bit skew. 16 ns is the read-clock period and is well inside the
# multi-cycle stability window.
set fifo_data [get_pins -hier -quiet -filter { \
    NAME =~ *rx_raw_fifo_i/rd_i_reg*/D || NAME =~ *rx_raw_fifo_i/rd_q_reg*/D}]
if {[llength $fifo_data] > 0} {
  set_max_delay -datapath_only -from [get_clocks -quiet rx_clk] -to $fifo_data 16.000
  puts "course overlay: datapath-only max_delay (16 ns) applied to [llength $fifo_data] rx_raw_fifo read-data pins"
}

# gp_ctrl[8] is quasi-static and crosses from sample_clk into adc_input_clk only
# through rx_ch2_adc_meta -> rx_ch2_adc_sync. Cut capture into the first ASYNC_REG
# stage; the second stage remains timed normally in the destination domain.
set rx_ch2_cdc [get_pins -hier -quiet -filter {NAME =~ *rx_ch2_adc_meta_reg/D}]
if {[llength $rx_ch2_cdc] > 0} {
  set_false_path -to $rx_ch2_cdc
  puts "course overlay: false_path applied to rx_ch2 ADC-domain synchronizer"
}
