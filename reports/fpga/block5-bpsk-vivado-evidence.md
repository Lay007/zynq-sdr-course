# Block 5 BPSK RTL: Vivado OOC implementation evidence

[Русская версия](block5-bpsk-vivado-evidence_ru.md)

## Result

Vivado 2021.1 synthesizes, places and routes every BPSK RTL module of Labs 5.6-5.11 out of
context on the course part `xc7z020clg400-2` with a `100 MHz` clock. All 13 tops are fully routed
with no DRC errors. Input and output ports are timed as if every neighbour were a register on the
same clock (0 ns input and output delay). **Twelve of the thirteen meet 100 MHz; the Gardner
symbol timing recovery does not.**

| Lab | Top | LUT | FF | DSP48E1 | BRAM | Post-route WNS at 100 MHz | Estimate |
|---|---|---:|---:|---:|---:|---:|---:|
| 5.7 | `bpsk_symbol_mapper` | 2 | 4 | 0 | 0 | +7.378 ns | |
| 5.7 | `bpsk_upsampler_8x` | 21 | 37 | 0 | 0 | +6.567 ns | |
| 5.6 | `bpsk_rrc_tx_fir` (65 taps, I and Q) | 148 | 2266 | 96 | 0 | +3.038 ns | about 144 MHz |
| 5.8 | `bpsk_rrc_rx_fir` (matched filter) | 148 | 2266 | 96 | 0 | +3.146 ns | about 146 MHz |
| 5.8 | `bpsk_symbol_timing_sampler` | 53 | 65 | 0 | 0 | +5.065 ns | |
| 5.8 | `bpsk_hard_decision` | 1 | 2 | 0 | 0 | +7.378 ns | |
| 5.8 | `bpsk_rx_bit_recovery_chain` | 251 | 2333 | 96 | 0 | +2.699 ns | about 137 MHz |
| 5.8 | `bpsk_symbol_timing_recovery` (Gardner loop) | 476 | 201 | 8 | 0 | **-13.447 ns**, 122 failing endpoints | about 43 MHz |
| 5.9 | `bpsk_frame_bit_source` | 36 | 18 | 0 | 0 | +5.225 ns | |
| 5.9 | `bpsk_framed_tx_chain` | 213 | 593 | 96 | 0 | +3.946 ns | about 165 MHz |
| 5.9 | `bpsk_ber_counter` | 287 | 203 | 0 | 0 | +2.826 ns | about 139 MHz |
| 5.10 | `bpsk_zynq_ber_top` | 688 | 3074 | 192 | 0 | +1.659 ns | about 120 MHz |
| 5.11 | `bpsk_zynq_ber_axi_lite` | 595 | 1995 | 144 | 0 | +1.124 ns | about 113 MHz |

The frequency estimate is `1 / (period - WNS)`; it describes the routed critical path, not a
characterized maximum clock. These are module-level numbers, not a board design: the integrated
Zynq build is reported separately in
[`integrated-zynq-implementation-summary.md`](integrated-zynq-implementation-summary.md).

## What the numbers say

**The RRC filters are expensive.** Each 65-tap filter is fully parallel and symmetric: the
testbench-verified structure pre-adds mirrored samples and multiplies 33 products per clock, for I
and for Q. Vivado maps it to 96 DSP48E1, so the Lab 5.10 top with a TX and an RX filter uses 192
of the 220 DSP slices on the XC7Z020 (87 %). The timing is comfortable (the adder tree is
registered stage by stage); the cost is area. Two observations for a later optimization, not
measured here: after the 8x upsampler seven of every eight TX input samples are zero, so a
polyphase TX filter needs about one eighth of the multipliers, and a BPSK Q channel carries no
information on TX.

The AXI-Lite top (Lab 5.11) uses 48 fewer DSP slices than the Lab 5.10 top although it contains
the same datapath. The Lab 5.10 top drives `tx_q` to a port; the AXI-Lite top exposes only
registers, and Vivado removes logic whose result never reaches an output. The difference equals
one channel of one filter, which is consistent with the TX Q path being removed.

**The Gardner loop does not meet 100 MHz.** `bpsk_symbol_timing_recovery` computes the whole loop
in one clock: NCO -> interpolation multiply (2 DSP48E1) -> sign-Gardner detector -> PI loop filter
-> next NCO step. The worst path runs from `nco_reg` to `w_step_reg` through 40 logic levels
(28 of them carry chains) in 22.8 ns against a 10 ns budget. This module is the "drop-in
alternative" of Lab 5.8b and is not instantiated in the Lab 5.10/5.11 tops with their default parameters, whose fixed-phase
`bpsk_symbol_timing_sampler` meets timing with +5.065 ns. The Gardner module and its alternative are selected by the
`TIMING_RECOVERY` parameter of `bpsk_rx_bit_recovery_chain` (default 0, fixed phase). Before the
loop runs on hardware at 100 MHz it needs pipelining. The loop filter and the NCO step update only
on the on-time strobe, once per symbol (every 8 input samples), and the interpolator is evaluated
on every strobe (about every 4 samples), so both have several clocks of slack in the loop's own
time scale; the work is to split the path without changing the loop's bit-exact behaviour.

**The remaining critical paths are fanout, not logic.** In the two top-level designs the worst
path has 0-1 logic levels and is more than 94 % routing: a valid signal driving the clock enables
of the matched filter's adder tree (Lab 5.10), and the AXI reset driving the reset pins of the
filter's product registers (Lab 5.11).

## Relation to the earlier Block 5 reports

[`block5-timing-summary.md`](block5-timing-summary.md) covers the four introductory modules
(`iq_passthrough`, `fir_iq_4tap`, `nco_mixer_iq`, `axis_iq_passthrough`) with synthesis only and a
clock-only constraint, so their port paths are untimed. This report uses the full OOC
implementation flow (placement and routing) and times the ports.

## Reproduction

From the repository root, with Vivado available through `VIVADO_BIN` or a standard Xilinx path:

```powershell
python tools/generate_block5_bpsk_vivado_reports.py
python tools/generate_block5_bpsk_vivado_reports.py --reuse    # re-parse without rerunning Vivado
python tools/generate_block5_bpsk_vivado_reports.py --top bpsk_symbol_timing_recovery
```

Each top is built in an in-memory project from the checked-in `bpsk_*.v` sources:
`synth_design -mode out_of_context`, `opt_design`, `place_design`, `phys_opt_design`,
`route_design`, then post-synthesis and post-route utilization, timing, route status and DRC
reports. Synthesis runs from the repository root so the `$readmemh` tap and frame-bit files
resolve (the log reports `bpsk_rrc_tx_fir_taps.mem` as read successfully). No project, checkpoint
or bitstream is written. The per-top constraints, raw reports and
`block5_bpsk_vivado_ooc_metrics.json` are in `block5_bpsk_vivado_ooc_raw/`, with date and host
lines normalized. The flow sets `general.maxThreads 1`; run one Vivado process at a time on a
16 GB machine.
