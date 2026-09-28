# Block 8 OFDM RTL: Vivado OOC implementation evidence

[Русская версия](block8-ofdm-vivado-evidence_ru.md)

## Result

Vivado 2021.1 synthesizes, places and routes every Block 8 OFDM RTL block out of context on
the course part `xc7z020clg400-2` with a `100 MHz` clock constraint. All seven are fully routed
with no DRC errors and **all clocked blocks meet 100 MHz** with the default, pipelined IFFT/FFT
schedule:

| Block | LUT | FF | DSP48E1 | BRAM | Post-route WNS at 100 MHz | Estimate |
|---|---:|---:|---:|---:|---:|---:|
| `ofdm_tx_cp16_path` (mapper, allocator, IFFT64, CP insertion) | 8321 | 2421 | 4 | 0 | +1.694 ns | about 120 MHz |
| `ofdm_cp16_remover` | 11 | 8 | 0 | 0 | +7.187 ns | |
| `ofdm_fft64_sequential` | 7572 | 2391 | 4 | 0 | +1.227 ns | about 114 MHz |
| `ofdm_subcarrier_extractor` | 16 | 0 | 0 | 0 | combinational, no clock | |
| `ofdm_one_tap_equalizer` | 148 | 72 | 4 | 0 | +7.141 ns | |
| `ofdm_pilot_phase_tracker` | 532 | 267 | 0 | 0 | +3.941 ns | |
| `ofdm_qpsk_demapper` | 3 | 0 | 0 | 0 | combinational, no clock | |

The frequency estimate is `1 / (period - WNS)`; it describes the routed critical path, not a
characterized maximum clock.

## Before and after: the one-cycle butterfly

The first implementation run used the teaching baseline, where the shared radix-2 butterfly does
the whole datapath in one clock (`PIPELINED = 0`, still available and still tested in CI). Both
transforms then missed 100 MHz by about 10 ns:

| Block | Baseline (`PIPELINED = 0`) | Pipelined (default) |
|---|---:|---:|
| `ofdm_tx_cp16_path` | WNS -10.234 ns, 1922 of 5155 endpoints failing, 8777 LUT | WNS +1.694 ns, 0 failing, 8321 LUT |
| `ofdm_fft64_sequential` | WNS -10.769 ns, 8938 LUT | WNS +1.227 ns, 7572 LUT |
| IFFT compute clocks per transform | 384 | 222 |

`ofdm_fft64_sequential` reuses the IFFT core (`FFT(x)/N = conj(IFFT(conj(x)))`), so both had the
same critical path: from the IFFT stage counter through operand and twiddle selection, the complex
multiply (2 DSP48E1), the add/subtract, rounding, Q1.15 saturation and the butterfly's
`saturation_count` register, all within one clock: 28 logic levels and 20.2 ns (TX) / 20.8 ns
(FFT) against a 10 ns budget.

The fix keeps the arithmetic bit for bit and changes only the schedule:

- `ofdm_ifft_butterfly` with `PIPELINED = 1` registers its inputs, the four products, the rounded
  twiddle product and the halved/saturated outputs: four clocks of latency, one butterfly per
  clock.
- `ofdm_ifft64_sequential` then issues a stage's 32 butterflies back to back, writes each result
  back four clocks later (addresses travel in a delay line) and waits for the pipeline to drain
  between stages. Inside a radix-2 stage every point belongs to exactly one butterfly, so reads
  and write-backs never collide.

The result is faster as well as timing-closed: 222 compute clocks instead of 384. All 16 OFDM
testbenches pass in both modes (`python tools/run_ofdm_rtl.py` and `--baseline`), including the
bit-exact vectors and both BER = 0 digital loopbacks.

## What limits it now

The new critical path is no longer arithmetic: it is the state register driving the write enable of
the 64-point working memory (1 logic level, 8.1 ns, 92 % of it routing). The transforms keep that
memory in fabric flip-flops and LUTs (0 BRAM tiles, 80 LUTs as distributed RAM in the TX path), so
one control signal fans out to about 2k flip-flops. Moving the working memory into block RAM is the
next step if more margin or fewer LUTs are needed; with two reads and two writes per clock in the
pipelined schedule it needs a banked memory layout, not a single dual-port BRAM.

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
lines normalized. The baseline numbers above come from the earlier run of the same flow
(commit `8120687`).

Run notes: the flow sets `general.maxThreads 1`. On the 16 GB machine used here, parallel Vivado
work ran out of memory and showed up as misleading "couldn't read file" errors on Vivado's own
scripts; run one Vivado process at a time.
