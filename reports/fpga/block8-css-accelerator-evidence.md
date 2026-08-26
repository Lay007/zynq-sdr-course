# Block 8 CSS accelerator: Vivado OOC implementation evidence

[Русская версия](block8-css-accelerator-evidence_ru.md)

## Result

Vivado 2021.1 fully routes `css_sf7_sequential_detector` out of context and
meets the `100 MHz` clock constraint on `xc7z020clg400-2`:

| Metric | Result |
|---|---:|
| WNS | `+0.526 ns` |
| TNS | `0.000 ns` |
| Failing endpoints | `0 / 2142` |
| Critical data-path delay | `9.412 ns` |
| Fully routed nets | `1562 / 1562` |
| Nets with routing errors | `0` |
| DRC error violations | `0` |
| Post-route critical-period estimate | `105.552 MHz` |

The frequency value is derived from the routed constraint and setup slack. It
is useful margin evidence, not a characterization of the maximum reliable
clock frequency.

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
out_of_context`, `opt_design`, `place_design`, `phys_opt_design`, and
`route_design`. It publishes normalized post-synthesis and post-route reports.
It does not create or commit a Vivado project, build directory, checkpoint,
bitstream, log, or journal.

## Utilization

| Resource | Used | XC7Z020 available | Share |
|---|---:|---:|---:|
| Slice LUT | 631 | 53,200 | 1.19% |
| Slice registers | 421 | 106,400 | 0.40% |
| BRAM tiles | 1.5 | 140 | 1.07% |
| DSP48E1 | 16 | 220 | 7.27% |

Post-synthesis utilization is 693 LUTs with the same register, BRAM, and DSP
counts. Placement-time physical synthesis combines 62 LUTs, producing the
631-LUT routed result. Hierarchical synthesis attributes 4 DSPs to dechirp, 12
DSPs to the DFT core, and no DSPs to the symbol buffer or peak detector. The
symbol buffer uses distributed RAM; Vivado also infers three RAMB18E1
primitives for lookup tables.

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

## Route and DRC interpretation

`report_route_status` marks the design `Fully Routed`: all 1,562 routable nets
are routed and none has a routing error. The final DRC report contains zero
error-severity violations and 46 warning-severity methodology violations:

- 44 warnings recommend deeper DSP48 input/output pipelining;
- one `RTSTAT-10` warning identifies internal result/status nets without
  routable loads in this isolated top level;
- one `ZPS7-1` warning notes that a complete Zynq design must instantiate PS7.

The DSP recommendations do not prevent the current 100 MHz timing closure.
They identify possible power and higher-frequency work. The other two warnings
are expected at the OOC boundary and must be rechecked after system integration.

## Evidence limits

- This is implemented OOC timing for the isolated detector, not timing closure
  of a complete PS/PL board design.
- AXI logic, PS7, clock/reset generation, floorplanning, and the complete design
  can change utilization and slack.
- Only internal `clk` paths are constrained. The 34 input and 161 output ports
  intentionally have no I/O delays; OOC ports also have no `HD.PARTPIN_LOCS`.
- No bitstream was generated and no hardware operation was tested.
- The next evidence step is an integrated AXI/PS wrapper, complete
  placed-and-routed timing, and a hardware smoke test.

Machine-readable and raw normalized reports are in
`reports/fpga/block8_css_vivado_ooc_raw/`.
