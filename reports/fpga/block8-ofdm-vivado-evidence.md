# Block 8 OFDM RTL: Vivado OOC implementation evidence

[Русская версия](block8-ofdm-vivado-evidence_ru.md)

## Result

Vivado 2021.1 synthesizes, places and routes every Block 8 OFDM RTL block out of context on
the course part `xc7z020clg400-2` with a `100 MHz` clock constraint, plus the pilot phase
corrector, the per-subcarrier channel equalizer (both modes) and the complete AXI4-Stream/AXI4-Lite
modem, and the fabric-memory variants of the transforms for comparison. All are fully routed with
no DRC errors. Input and output ports are timed as if every neighbour were a register on the same
clock (0 ns input and output delay, see [Port paths](#port-paths-a-correction)). With the default
configuration (pipelined schedule, block-RAM working memory), **every clocked block except the
one-clock teaching equalizer meets 100 MHz**:

| Block | LUT | FF | DSP48E1 | BRAM | Post-route WNS at 100 MHz | Estimate |
|---|---:|---:|---:|---:|---:|---:|
| `ofdm_tx_cp16_path` (mapper, allocator, IFFT64, CP insertion) | 886 | 362 | 4 | 1 | +1.650 ns | about 120 MHz |
| `ofdm_cp16_remover` | 11 | 8 | 0 | 0 | +5.835 ns | |
| `ofdm_fft64_sequential` | 833 | 329 | 4 | 1 | +1.487 ns | about 117 MHz |
| `ofdm_subcarrier_extractor` | 16 | 0 | 0 | 0 | combinational, no clock | |
| `ofdm_one_tap_equalizer` (`PIPELINED = 0`, one clock) | 147 | 72 | 4 | 0 | **-1.077 ns**, 32 failing endpoints | about 90 MHz |
| `ofdm_pilot_phase_tracker` | 532 | 267 | 0 | 0 | +4.022 ns | |
| `ofdm_pilot_phase_corrector` (tracker, symbol buffer, pipelined equalizer) | 707 | 364 | 4 | 1 | +0.568 ns | about 106 MHz |
| `ofdm_channel_equalizer` (per-subcarrier, training symbol, `NORMALIZE = 0`) | 331 | 141 | 4 | 1 | +0.962 ns | about 111 MHz |
| `ofdm_channel_equalizer_zf` (the same, `NORMALIZE = 1`: zero-forcing, CORDIC `1/abs(G)^2`) | 966 | 538 | 10 | 0.5 | +2.677 ns | about 137 MHz |
| `ofdm_cfo_corrector` (CP correlation, vectoring CORDIC, NCO, pipelined rotation CORDIC) | 2382 | 1519 | 10 | 0 | +2.412 ns | about 132 MHz |
| `ofdm_qpsk_demapper` | 3 | 0 | 0 | 0 | combinational, no clock | |
| `ofdm_axi_modem` (TX and RX chains, CFO corrector, zero-forcing channel equalizer, AXI4-Stream/AXI4-Lite) | 5895 | 3178 | 32 | 3.5 | +0.853 ns | about 109 MHz |
| `ofdm_tx_cp16_path_fabric` (`BRAM_MEMORY = 0`) | 8151 | 2403 | 4 | 0 | +0.832 ns | about 109 MHz |
| `ofdm_fft64_sequential_fabric` (`BRAM_MEMORY = 0`) | 7307 | 2423 | 4 | 0 | +0.597 ns | about 106 MHz |
| `ofdm_axi_modem_fabric` (`BRAM_MEMORY = 0`) | 19602 | 7295 | 32 | 1.5 | +0.220 ns | about 102 MHz |
| `ofdm_tx_cp16_path_qam16` (`MODULATION = 1`: 16-QAM mapper) | 895 | 370 | 4 | 1 | +1.771 ns | about 122 MHz |
| `ofdm_axi_modem_qam16` (`MODULATION = 1`: 16-QAM mapper and slicer) | 5966 | 3216 | 32 | 3.5 | +0.584 ns | about 106 MHz |

The frequency estimate is `1 / (period - WNS)`; it describes the routed critical path, not a
characterized maximum clock. Rows with a suffix are the same module with a parameter override.

## Working memory in block RAM

Each transform keeps 64 complex points. In fabric they cost about 8k LUTs and 2.4k flip-flops per
transform, and one control signal fanned out to all of them. `BRAM_MEMORY = 1` (now the default
with the pipelined schedule) puts them in two 32-word block-RAM banks: bank = XOR of the six address
bits, word = `address[5:1]`. The two points of a radix-2 butterfly differ in exactly one address
bit, so they always sit in different banks, and each bank serves one read and one write per clock;
that is exactly two reads and two write-backs per clock without a conflict. Block-RAM reads are
registered, so a transform takes 229 compute clocks instead of 222.

| Block | Fabric memory | Block-RAM memory |
|---|---:|---:|
| `ofdm_tx_cp16_path` | 8151 LUT, 2403 FF, +0.832 ns | 886 LUT, 362 FF, 1 BRAM, +1.650 ns |
| `ofdm_fft64_sequential` | 7307 LUT, 2423 FF, +0.597 ns | 833 LUT, 329 FF, 1 BRAM, +1.487 ns |
| `ofdm_axi_modem` | 19602 LUT, 7295 FF, +0.220 ns | 5895 LUT, 3178 FF, 3.5 BRAM, +0.853 ns |

About a ninth of the transforms' LUTs and more timing margin. All 23 OFDM testbenches pass in both memory
modes (`python tools/run_ofdm_rtl.py` and `--fabric`), and the one-cycle baseline (`--baseline`)
keeps fabric memory because block RAM cannot serve its schedule.

## Zero-forcing equalizer: rounding over three clocks

The first `NORMALIZE = 1` version formed `round((Y*conj(G)) * z / 2^sh)` in one clock: magnitude of
a 53-bit product, adding `2^(sh-1)` for a variable `sh`, a variable shift, the sign and the
saturation test, 26 carry chains. It missed 100 MHz with WNS -2.227 ns (the AXI modem with it:
-2.641 ns). Splitting it into sign/magnitude, `+ 2^(sh-1)`, and shift with an OR-reduced
saturation test, and replacing the CORDIC's barrel shift by registers that shift one place per
iteration, gives +2.677 ns with the same arithmetic (the same vectors pass). The modem with the
zero-forcing equalizer then meets 100 MHz with more margin than the modem without it had.

## CFO corrector: one more clock for the normalization

The first `ofdm_cfo_corrector` took the magnitudes of the 48-bit accumulated correlation, compared
them and searched the top bit in one clock (19 logic levels): +0.147 ns, barely met. Registering the
magnitudes one clock earlier gives +2.412 ns with the same arithmetic; the worst path is then a
vectoring CORDIC iteration.

## AXI modem: what the CFO corrector costs

Since core version 3.0 the modem has the CFO corrector in front of the CP removal by default
(`CFO_CORR = 1`). Against the previous build (3509 LUT, 1674 FF, 22 DSP, +1.241 ns) it adds 2386 LUT,
1504 FF and 10 DSP, practically the standalone corrector (2382 LUT, 1519 FF, 10 DSP). The 16-QAM
variant (`MODULATION = 1`) costs another 71 LUT and 38 FF for the mapper and the slicer. Timing
still closes, with less margin: the worst path is unchanged (the pilot corrector's one-tap
equalizer), only longer through routing in a fuller device.

## A memory reset that cost 2300 flip-flops

The first version of `ofdm_channel_equalizer` cleared its 64-entry coefficient memory (2 x 18 bits
per entry) in the reset branch. A memory with a reset cannot be a RAM, so Vivado built it from
flip-flops: 995 LUTs, 2445 flip-flops, WNS +0.909 ns. The reset was not needed, because the
training symbol writes all 64 entries (zero on the null bins) before any data symbol reads them.
Without it the same RTL, bit-exact with the same vectors, maps the memory to one block RAM:
332 LUTs, 141 flip-flops, WNS +1.152 ns. A similar trap came with the zero-forcing option: with
`NORMALIZE = 0` Vivado kept the unused CORDIC engine (2 DSP48E1 for `abs(G)^2`) and its second read
port moved the memory into LUT RAM (452 LUTs, 6 DSP, 0 BRAM). Gating the engine with the parameter
restores 331 LUTs, 4 DSP and the block RAM.

## Port paths: a correction

The first version of this report constrained only the clock. Vivado then leaves every path from
an input port to the first register, and from the last register to an output port, untimed
(`check_timing` lists them under `no_input_delay` / `no_output_delay`). For most blocks this made
no difference, but it hid the equalizer's real path: its multipliers are fed straight from the
input ports, so only the small `saturation_count` increment was timed and the block was reported
at +7.141 ns.

Timed properly, the one-clock equalizer's path is input -> two cascaded DSP48E1 -> add/subtract ->
rounding -> Q1.15 saturation -> `saturation_count`, 24 logic levels and 12.4 ns: WNS -1.077 ns.
The pilot phase corrector showed the same path with a buffer read in front of it (13.9 ns,
WNS -4.024 ns). The fix mirrors the butterfly: `ofdm_one_tap_equalizer` with `PIPELINED = 1`
registers its inputs, the four products and the output (three clocks of latency, one sample per
clock, identical arithmetic) and adds the saturation count one clock later. The corrector and the
AXI modem use that form; the standalone default stays `PIPELINED = 0` for teaching, and both are
tested in CI.

## Before and after: the one-clock butterfly

The first implementation run used the teaching baseline, where the shared radix-2 butterfly does
the whole datapath in one clock (`PIPELINED = 0`, still available and still tested in CI). Both
transforms then missed 100 MHz by about 10 ns (register-to-register, so the missing port delays do
not change this comparison; fabric memory in both columns):

| Block | Baseline (`PIPELINED = 0`) | Pipelined, fabric memory |
|---|---:|---:|
| `ofdm_tx_cp16_path` | WNS -10.234 ns, 1922 of 5155 endpoints failing, 8777 LUT | WNS +0.832 ns, 0 failing, 8151 LUT |
| `ofdm_fft64_sequential` | WNS -10.769 ns, 8938 LUT | WNS +0.597 ns, 7307 LUT |
| IFFT compute clocks per transform | 384 | 222 (229 with block-RAM memory) |

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

## What limits it now

With the working memory in block RAM the remaining critical paths are arithmetic again, with
margin: in the TX path and the FFT the butterfly's last stage (rounding, Q1.15 saturation and the
saturation counter, 12-13 logic levels, 8.3-8.5 ns), and in the AXI modem the pipelined one-tap
equalizer of the pilot corrector (round, saturate, count; 14-15 levels, 9.1-9.3 ns, of which
about 42-46 % is routing). In the fabric-memory variants the worst path is the state register
driving the writes into the 64-point memory: one logic level, 9.0-9.6 ns, about 95 % of it routing
to some 2k flip-flops.

## Reproduction

From the repository root, with Vivado available through `VIVADO_BIN` or a standard Xilinx path:

```powershell
python tools/generate_block8_ofdm_vivado_reports.py
python tools/generate_block8_ofdm_vivado_reports.py --reuse    # re-parse without rerunning Vivado
python tools/generate_block8_ofdm_vivado_reports.py --top ofdm_pilot_phase_tracker
python tools/generate_block8_ofdm_vivado_reports.py --top ofdm_axi_modem_fabric
python tools/generate_block8_ofdm_vivado_reports.py --top ofdm_axi_modem_qam16
```

A `--top` run rewrites the metrics JSON with only the tops it built; run `--reuse` afterwards to
collect every configuration again.

Each configuration is built in an in-memory project from the checked-in `ofdm_*.v` sources:
`synth_design -mode out_of_context` (with `-generic` overrides for the suffixed rows),
`opt_design`, `place_design`, `phys_opt_design`, `route_design`, then post-synthesis and post-route
utilization, timing, route status and DRC reports. No project, checkpoint or bitstream is written.
The constraints written for each configuration (`<name>.xdc`), the raw reports and
`block8_ofdm_vivado_ooc_metrics.json` are in `block8_ofdm_vivado_ooc_raw/`, with date and host lines
normalized. The baseline numbers above come from the earlier run of the same flow (commit
`8120687`). The zero-forcing and modem runs predate the change that gates the CORDIC engine for
`NORMALIZE = 0`; with `NORMALIZE = 1` that gate is constant true, so their logic is unchanged.

Run notes: the flow sets `general.maxThreads 1`. On the 16 GB machine used here, parallel Vivado
work ran out of memory and showed up as misleading "couldn't read file" errors on Vivado's own
scripts; run one Vivado process at a time. The same error also came from a stale `.Xil` directory
left in the report directory by an interrupted run; deleting it fixed the rerun. The modem and the
fabric FFT take 40-70 minutes each here, most of it in the router fixing hold on the port paths.
