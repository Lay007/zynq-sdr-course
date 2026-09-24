# Block 8 OFDM RTL: Vivado OOC implementation evidence

[Русская версия](block8-ofdm-vivado-evidence_ru.md)

## Result

Vivado 2021.1 synthesizes, places and routes every Block 8 OFDM RTL block out of context on
the course part `xc7z020clg400-2` with a `100 MHz` clock constraint. All seven are fully routed
with no DRC errors. Two of them, the ones built on the shared radix-2 butterfly, **miss 100 MHz
by a wide margin**:

| Block | LUT | FF | DSP48E1 | BRAM | Post-route WNS at 100 MHz | Estimate |
|---|---:|---:|---:|---:|---:|---:|
| `ofdm_tx_cp16_path` (mapper, allocator, IFFT64, CP insertion) | 8777 | 2276 | 4 | 0 | **-10.234 ns**, 1922 of 5155 endpoints failing | about 49 MHz |
| `ofdm_cp16_remover` | 11 | 8 | 0 | 0 | +7.187 ns | |
| `ofdm_fft64_sequential` | 8938 | 2255 | 4 | 0 | **-10.769 ns** | about 48 MHz |
| `ofdm_subcarrier_extractor` | 16 | 0 | 0 | 0 | combinational, no clock | |
| `ofdm_one_tap_equalizer` | 148 | 72 | 4 | 0 | +7.141 ns | |
| `ofdm_pilot_phase_tracker` | 532 | 267 | 0 | 0 | +3.941 ns | |
| `ofdm_qpsk_demapper` | 3 | 0 | 0 | 0 | combinational, no clock | |

The frequency estimate is `1 / (period - WNS)`; it describes the routed critical path, not a
characterized maximum clock.

## Why the transforms miss timing

The critical path of both transforms is the same, because `ofdm_fft64_sequential` reuses the
IFFT core (`FFT(x)/N = conj(IFFT(conj(x)))`). It starts at the IFFT stage counter
(`ifft/stage_reg`), goes through the operand and twiddle selection, the complex multiply
(2 DSP48E1), the add/subtract, the rounding, the Q1.15 saturation, and ends in the butterfly's
`saturation_count` register, all within one clock: 28 logic levels (13 CARRY4) and a data-path
delay of 20.2 ns (TX) / 20.8 ns (FFT) against a 10 ns budget. This follows directly from the
butterfly's documented contract of one-clock latency.

The transforms also hold their 64-point working memory in fabric registers and LUTs, not in
block RAM (0 BRAM tiles, 80 LUTs as distributed RAM in the TX path), which is why they are two
orders of magnitude larger than the other blocks.

What would fix it, in order of cost: register the butterfly products before the add, move
rounding/saturation and the saturation counter into a following stage (the same pattern as the
Lab 5.2 FIR, where a separate rounding/saturation stage moved WNS from -0.125 ns to +5.35 ns),
and then map the working memory to block RAM. Each extra butterfly stage changes the IFFT
schedule, so the sequential controller and its testbenches must change with it. None of this
is done yet; the RTL is simulation-verified (bit-exact against the Python model, BER 0 in the
digital loopbacks) but it is not yet a 100 MHz FPGA design.

## Reproduction

From the repository root, with Vivado available through `VIVADO_BIN` or a standard Xilinx path:

```powershell
python tools/generate_block8_ofdm_vivado_reports.py
python tools/generate_block8_ofdm_vivado_reports.py --reuse    # re-parse without rerunning Vivado
python tools/generate_block8_ofdm_vivado_reports.py --top ofdm_pilot_phase_tracker
```

Each top is built in an in-memory project from the checked-in `ofdm_*.v` sources:
`synth_design -mode out_of_context`, `opt_design`, `place_design`, `phys_opt_design`,
`route_design`, then post-synthesis and post-route utilization, timing, route status and DRC
reports. No project, checkpoint or bitstream is written. The raw reports and
`block8_ofdm_vivado_ooc_metrics.json` are in `block8_ofdm_vivado_ooc_raw/`, with date and host
lines normalized.

Run note: on the machine used for this report, multi-threaded synthesis twice failed to read a
file of the Vivado installation (`couldn't read file ... unimacro_vhdl.tcl`, then `common.tcl`,
both present on disk). The flow therefore now sets `general.maxThreads 1`. The six other tops in this report were
built before that setting was added, with multi-threaded synthesis.
