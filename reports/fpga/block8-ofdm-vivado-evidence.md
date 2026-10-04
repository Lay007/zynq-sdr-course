# Block 8 OFDM RTL: Vivado OOC implementation evidence

[Русская версия](block8-ofdm-vivado-evidence_ru.md)

## Result

Vivado 2021.1 synthesizes, places and routes every Block 8 OFDM RTL block out of context on
the course part `xc7z020clg400-2` with a `100 MHz` clock constraint, plus the pilot phase
corrector, the per-subcarrier channel equalizer and the complete AXI4-Stream/AXI4-Lite modem.
All ten are fully routed with no DRC
errors. Input and output ports are timed as if every neighbour were a register on the same clock
(0 ns input and output delay, see [Port paths](#port-paths-a-correction)). With the default
pipelined schedules, **every clocked block except the one-clock teaching equalizer meets
100 MHz**:

| Block | LUT | FF | DSP48E1 | BRAM | Post-route WNS at 100 MHz | Estimate |
|---|---:|---:|---:|---:|---:|---:|
| `ofdm_tx_cp16_path` (mapper, allocator, IFFT64, CP insertion) | 8321 | 2421 | 4 | 0 | +1.335 ns | about 115 MHz |
| `ofdm_cp16_remover` | 11 | 8 | 0 | 0 | +5.835 ns | |
| `ofdm_fft64_sequential` | 7575 | 2391 | 4 | 0 | +0.738 ns | about 108 MHz |
| `ofdm_subcarrier_extractor` | 16 | 0 | 0 | 0 | combinational, no clock | |
| `ofdm_one_tap_equalizer` (`PIPELINED = 0`, one clock) | 147 | 72 | 4 | 0 | **-1.077 ns**, 32 failing endpoints | about 90 MHz |
| `ofdm_pilot_phase_tracker` | 532 | 267 | 0 | 0 | +4.022 ns | |
| `ofdm_pilot_phase_corrector` (tracker, symbol buffer, pipelined equalizer) | 707 | 364 | 4 | 1 | +0.568 ns | about 106 MHz |
| `ofdm_channel_equalizer` (per-subcarrier, training symbol) | 332 | 141 | 4 | 1 | +1.152 ns | about 113 MHz |
| `ofdm_qpsk_demapper` | 3 | 0 | 0 | 0 | combinational, no clock | |
| `ofdm_axi_modem` (TX and RX chains with AXI4-Stream/AXI4-Lite) | 16711 | 5245 | 12 | 1 | +0.775 ns | about 108 MHz |

The frequency estimate is `1 / (period - WNS)`; it describes the routed critical path, not a
characterized maximum clock.

## A memory reset that cost 2300 flip-flops

The first version of `ofdm_channel_equalizer` cleared its 64-entry coefficient memory (2 x 18 bits
per entry) in the reset branch. A memory with a reset cannot be a RAM, so Vivado built it from
flip-flops: 995 LUTs, 2445 flip-flops, WNS +0.909 ns. The reset was not needed, because the
training symbol writes all 64 entries (zero on the null bins) before any data symbol reads them.
Without it the same RTL, bit-exact with the same vectors, maps the memory to one block RAM:
332 LUTs, 141 flip-flops, WNS +1.152 ns.

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
not change this comparison):

| Block | Baseline (`PIPELINED = 0`) | Pipelined (default) |
|---|---:|---:|
| `ofdm_tx_cp16_path` | WNS -10.234 ns, 1922 of 5155 endpoints failing, 8777 LUT | WNS +1.335 ns, 0 failing, 8321 LUT |
| `ofdm_fft64_sequential` | WNS -10.769 ns, 8938 LUT | WNS +0.738 ns, 7575 LUT |
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

The result is faster as well as timing-closed: 222 compute clocks instead of 384. All 18 OFDM
testbenches pass in both modes (`python tools/run_ofdm_rtl.py` and `--baseline`), including the
bit-exact vectors and the BER = 0 loopbacks.

## What limits it now

The remaining critical paths are not arithmetic; they are about 90 % routing and come from the
64-point working memory, which the transforms keep in fabric flip-flops and LUTs (0 BRAM tiles
in the transforms):

- TX path: the IFFT stage counter selecting butterfly operands out of that memory into the DSP
  input registers (4 logic levels, 8.2 ns);
- FFT: the output index register reading a bin out of the memory to the `bin_im` port (7 levels,
  7.6 ns);
- AXI modem: the same FFT output read, through the combinational subcarrier extractor, into the
  pilot tracker's accumulator (13 levels, 9.2 ns).

Moving the working memory into block RAM is the next step if more margin or fewer LUTs are needed;
with two reads and two writes per clock in the pipelined schedule it needs a banked memory layout,
not a single dual-port BRAM. A register slice between the FFT and the extractor would also relieve
the modem's path.

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
reports. No project, checkpoint or bitstream is written. The constraints written for each top
(`<top>.xdc`), the raw reports and `block8_ofdm_vivado_ooc_metrics.json` are in
`block8_ofdm_vivado_ooc_raw/`, with date and host lines normalized. The baseline numbers above
come from the earlier run of the same flow (commit `8120687`).

Run notes: the flow sets `general.maxThreads 1`. On the 16 GB machine used here, parallel Vivado
work ran out of memory and showed up as misleading "couldn't read file" errors on Vivado's own
scripts; run one Vivado process at a time. The same error also came from a stale `.Xil` directory
left in the report directory by an interrupted run; deleting it fixed the rerun.
