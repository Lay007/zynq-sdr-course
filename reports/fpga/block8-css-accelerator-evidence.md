# Block 8 CSS accelerator: Vivado OOC evidence

[Русская версия](block8-css-accelerator-evidence_ru.md)

## Result

Vivado 2021.1 out-of-context post-synthesis analysis of
`css_sf7_sequential_detector` meets the `100 MHz` clock constraint on
`xc7z020clg400-2`:

| Metric | Result |
|---|---:|
| WNS | `+1.006 ns` |
| TNS | `0.000 ns` |
| Failing endpoints | `0 / 2142` |
| Critical data-path delay | `8.888 ns` |
| Post-synthesis Fmax estimate | `111.185 MHz` |

The Fmax value is an estimate derived from the post-synthesis constraint and
slack. It is not a placed-and-routed maximum clock claim.

## Reproduction

Run from the repository root on Windows with Vivado available at the configured
`VIVADO_BIN` or under a standard Xilinx installation path:

```powershell
python tools/generate_block8_css_vivado_reports.py
```

To validate and republish an existing report directory without rerunning
Vivado:

```powershell
python tools/generate_block8_css_vivado_reports.py --reuse
```

The flow creates an in-memory project, reads only the checked-in RTL and ROM
tables, constrains `clk` to `10.000 ns`, and runs `synth_design -mode
out_of_context`. It does not create or commit a Vivado project, build directory,
checkpoint, bitstream, log, or journal.

## Utilization

| Resource | Used | XC7Z020 available | Share |
|---|---:|---:|---:|
| Slice LUT | 693 | 53,200 | 1.30% |
| Slice registers | 421 | 106,400 | 0.40% |
| BRAM tiles | 1.5 | 140 | 1.07% |
| DSP48E1 | 16 | 220 | 7.27% |

Hierarchical synthesis attributes 4 DSPs to dechirp, 12 DSPs to the DFT core,
and no DSPs to the symbol buffer or peak detector. The symbol buffer uses
distributed RAM; Vivado also inferred three RAMB18E1 primitives for lookup
tables after the timing pipeline changes.

## Latency and throughput

The WSL/Icarus regressions prove the cycle counts below. Rates use the constrained
`100 MHz` clock, not the unproven Fmax estimate.

| Metric | Cycles | Result at 100 MHz |
|---|---:|---:|
| Sequential 128-point DFT | 16,640 | 166.400 us |
| Final accepted input to `done` | 16,644 | 166.440 us |
| First accepted input to `done` | 16,771 | 167.710 us |
| Symbol initiation interval | 16,772 | 5,962.318 symbols/s |
| Sustained accepted-sample rate | — | 763,176.723 samples/s |

The sustained rate assumes 128 consecutive accepted samples followed by the
mandatory processing interval. Samples cannot be accepted continuously while
the sequential DFT is busy. At the educational SF7 configuration with
`BW = 125 kHz` and one sample per chip, the required rate is `125,000 samples/s`
and `976.5625 symbols/s`, below this architectural 100 MHz rate.

## Timing changes

Two behavior-preserving pipeline boundaries were required:

- the DFT registers each scaled complex term before the accumulator recurrence;
- the dechirp front end registers the reference-ROM coefficient with its
  matching IQ sample before the complex multiplier.

All 128 complex DFT bins remain bit-exact against the Python reference. The
integrated regression still passes all 128 noiseless symbols and deterministic
CFO/noise cases.

## Evidence limits

- This is out-of-context post-synthesis timing, not implementation timing.
- Placement, routing, clock-tree interaction, AXI integration, and the complete
  board design can change utilization and slack.
- Only the internal `clk` path is constrained; port-level input/output timing is
  intentionally outside this OOC measurement.
- No bitstream was generated and no hardware operation was tested.
- The next evidence step is an implemented OOC or integrated placed-and-routed
  report using the same `100 MHz` constraint.

Machine-readable and raw normalized reports are in
`reports/fpga/block8_css_vivado_ooc_raw/`.
