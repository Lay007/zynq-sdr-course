# Block 5 BPSK RTL: Vivado OOC implementation evidence

[Русская версия](block5-bpsk-vivado-evidence_ru.md)

## Result

Vivado 2021.1 synthesizes, places and routes every BPSK RTL module of Labs 5.6-5.11, and the four
introductory modules of Labs 5.1-5.4, out of context on the course part `xc7z020clg400-2` with a
`100 MHz` clock. All 17 tops, plus the one-clock teaching form of the Gardner loop, are fully
routed with no DRC errors. Input and output ports are timed as if every neighbour were a register
on the same clock (0 ns input and output delay). **All 13 BPSK modules meet 100 MHz.** The Gardner
symbol timing recovery needed a pipelined schedule for that; its one-clock teaching form
(`PIPELINED = 0`) is listed as well and misses by 9.4 ns. Of the introductory modules, the FIR and
the NCO mixer miss by a fraction of a nanosecond.

| Lab | Top | LUT | FF | DSP48E1 | BRAM | Post-route WNS at 100 MHz | Estimate |
|---|---|---:|---:|---:|---:|---:|---:|
| 5.1 | `iq_passthrough` | 1 | 33 | 0 | 0 | +7.320 ns | |
| 5.2 | `fir_iq_4tap` | 117 | 129 | 4 | 0 | **-0.247 ns**, 16 failing endpoints | about 98 MHz |
| 5.3 | `nco_mixer_iq` | 110 | 43 | 4 | 0 | **-0.361 ns**, 16 failing endpoints | about 97 MHz |
| 5.4 | `axis_iq_passthrough` | 4 | 34 | 0 | 0 | +6.539 ns | |
| 5.7 | `bpsk_symbol_mapper` | 2 | 4 | 0 | 0 | +7.378 ns | |
| 5.7 | `bpsk_upsampler_8x` | 21 | 37 | 0 | 0 | +6.567 ns | |
| 5.6 | `bpsk_rrc_tx_fir` (65 taps, I and Q) | 148 | 2266 | 96 | 0 | +3.038 ns | about 144 MHz |
| 5.7 | `bpsk_rrc_tx_polyphase` (upsampler + TX FIR as one polyphase filter) | 404 | 541 | 14 | 0 | +3.233 ns | about 148 MHz |
| 5.8 | `bpsk_rrc_rx_fir` (matched filter) | 148 | 2266 | 96 | 0 | +3.146 ns | about 146 MHz |
| 5.8 | `bpsk_symbol_timing_sampler` | 53 | 65 | 0 | 0 | +5.065 ns | |
| 5.8 | `bpsk_hard_decision` | 1 | 2 | 0 | 0 | +7.378 ns | |
| 5.8 | `bpsk_rx_bit_recovery_chain` | 251 | 2333 | 96 | 0 | +2.699 ns | about 137 MHz |
| 5.8 | `bpsk_symbol_timing_recovery` (Gardner loop, `PIPELINED = 1`) | 967 | 659 | 2 | 0 | +0.335 ns | about 103 MHz |
| 5.8 | `bpsk_symbol_timing_recovery_pipelined0` (the same module, `PIPELINED = 0`) | 338 | 201 | 2 | 0 | **-9.390 ns**, 122 failing endpoints | about 52 MHz |
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
registered stage by stage); the cost is area.

On the TX side most of that area multiplies zeros: after the 8x upsampler seven of every eight
filter inputs are zero. `bpsk_rrc_tx_polyphase` replaces the upsampler and the TX filter with one
polyphase filter: for output phase p only taps p, p+8, ..., p+64 meet a symbol, so one output per
clock needs 9 multipliers per channel whose coefficients change with p. It produces the same
samples on the same clocks as the pair (`tb_bpsk_rrc_tx_polyphase_equivalence.v`, 600 random
full-scale symbols with gaps, compared every clock) and uses 14 DSP48E1 instead of 96 and 541
flip-flops instead of 2303, at +3.233 ns. The price is 404 LUTs instead of 169, mostly the
coefficient multiplexers. The receive filter cannot do this: its input is a full-rate signal with
no zeros. (A further saving not used here: a BPSK Q channel carries no information on TX.)

The AXI-Lite top (Lab 5.11) uses 48 fewer DSP slices than the Lab 5.10 top although it contains
the same datapath. The Lab 5.10 top drives `tx_q` to a port; the AXI-Lite top exposes only
registers, and Vivado removes logic whose result never reaches an output. The difference equals
one channel of one filter, which is consistent with the TX Q path being removed.

**The Gardner loop needed a different schedule to meet 100 MHz.** The loop is a recursion over
one sample: at a strobe, NCO -> mu -> interpolation multiply -> add -> saturate -> sign-Gardner
error -> PI loop filter -> clamp -> next NCO step, and the next sample already needs that step.
The module is the "drop-in alternative" of Lab 5.8b, selected by the `TIMING_RECOVERY` parameter
of `bpsk_rx_bit_recovery_chain` (default 0: the fixed-phase `bpsk_symbol_timing_sampler`, +5.065
ns), so the Lab 5.10/5.11 tops do not contain it by default. Three measured steps:

| Version | LUT | FF | DSP48E1 | WNS at 100 MHz | Worst path |
|---|---:|---:|---:|---:|---|
| Original (commit `3d9aee8`): 32-bit x 32-bit interpolation multiply | 476 | 201 | 8 | -13.447 ns | 40 levels, 22.8 ns |
| `PIPELINED = 0`: same one-clock loop, 17-bit x 17-bit multiply | 338 | 201 | 2 | -9.390 ns | 34 levels, 18.9 ns |
| `PIPELINED = 1` (default): two-clock-late update with lookahead | 967 | 659 | 2 | +0.335 ns | 20 levels, 9.5 ns |

The interpolation operands fit in 17 bits (`x - x_prev` and `mu` in `[0, 1)`), so declaring them
that wide gives the same products from one DSP48E1 per channel instead of a cascade; that alone
removes 4 ns. The rest needs the schedule changed without changing a single output value:

- After a strobe the next one is at least three samples away when `3 * W_MAX <= 1.0` (55296 <=
  65536 at 8 samples per symbol; the module refuses `PIPELINED = 1` otherwise). So the strobe clock
  only captures the operands, the product is registered in the next clock, and the clock after that
  forms the symbol, the timing error and the loop update. The samples consumed in between stepped
  the NCO with the old step; the update rewrites the NCO as "NCO after the strobe - k * new step",
  k = 0, 1 or 2.
- The timing error has three values, so the three possible integrator values, steps and NCO values
  are computed and registered at the strobe, and the error only selects one (lookahead). An
  intermediate version computed the candidates combinationally; Vivado merged the selection back
  into one subtraction after the multiplexer and the path stayed at -4.6 ns. Registering the
  candidates is what keeps the selection a plain multiplexer.

The price is area: 659 instead of 201 flip-flops and twice the LUTs, mostly the nine registered
32-bit candidates. `tb_bpsk_symbol_timing_recovery_equivalence.v` feeds both versions the same
drifted burst (with random idle clocks between samples, so 0, 1 and 2 consumed samples all occur)
and requires every output symbol to match in I and Q; the model bit check and the full BER chain
with the loop enabled pass unchanged.

**The remaining critical paths are fanout, not logic.** In the two top-level designs the worst
path has 0-1 logic levels and is more than 94 % routing: a valid signal driving the clock enables
of the matched filter's adder tree (Lab 5.10), and the AXI reset driving the reset pins of the
filter's product registers (Lab 5.11).

## The four introductory modules (Labs 5.1-5.4)

The first Block 5 timing report, [`block5-timing-summary.md`](block5-timing-summary.md), ran
synthesis only and constrained only the clock. Re-run with this flow (placement, routing and
timed ports), the two arithmetic modules still miss 100 MHz by a fraction of a nanosecond, and the
numbers moved in both directions:

| Module | Synthesis only, clock-only constraint | This flow |
|---|---:|---:|
| `iq_passthrough` | no timed path (input to register untimed) | +7.320 ns |
| `fir_iq_4tap` | -0.125 ns | -0.247 ns |
| `nco_mixer_iq` | -0.807 ns | -0.361 ns |
| `axis_iq_passthrough` | +8.064 ns | +6.539 ns |

Post-synthesis timing uses estimated wire delays; after placement and routing they are real, and
`phys_opt_design` can also shorten a path, which is why the NCO improved while the FIR got slightly
worse. Both worst paths are the same kind: two cascaded DSP48E1 products followed by the
add/round/saturate carry chains into the output register, about 10.1-10.3 ns in one clock (the
FIR with 20 logic levels, the NCO with 14). Registering the sum before rounding and saturation is
the fix discussed in Lab 5.2.

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
python tools/generate_block5_bpsk_vivado_reports.py --top bpsk_symbol_timing_recovery_pipelined0
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
