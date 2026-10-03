# Block 5 FPGA Evidence

This page is the nav-visible entrypoint for the curated Vivado evidence packages for Block 5 and the integrated course design.

## Scope

The current package is based on Vivado 2021.1 out-of-context synthesis for the four educational HDL modules:

- `iq_passthrough`
- `fir_iq_4tap`
- `nco_mixer_iq`
- `axis_iq_passthrough`

The run targets `xc7z020clg400-2` and uses a `10.000 ns` / `100.000 MHz` clock constraint aligned with `FPGA0 = 100.000000 MHz` from the preserved PS7 board summary.

## Curated artifacts

| Artifact | Purpose | Source path |
|---|---|---|
| Board-level summary | Top-level LUT/FF/DSP/BRAM/Fmax snapshot | `reports/fpga/z7020-resource-summary-template.md` |
| Utilization summary | Per-module utilization digest | `reports/fpga/block5-utilization-summary.md` |
| Timing summary | WNS/TNS/data-path timing snapshot | `reports/fpga/block5-timing-summary.md` |
| BPSK OOC implementation (Labs 5.6-5.11) | Placed-and-routed LUT/FF/DSP/WNS for the 13 BPSK modules, port paths timed | `reports/fpga/block5-bpsk-vivado-evidence.md` |
| Latency and throughput notes | One-cycle pipeline and streaming behaviour | `reports/fpga/block5-latency-throughput-notes.md` |
| Raw metrics JSON | Machine-readable run summary | `reports/fpga/vivado_ooc_raw/block5_vivado_ooc_metrics.json` |
| Integrated implementation summary | Placed-and-routed top-level result | `reports/fpga/integrated-zynq-implementation-summary.md` |
| Integrated metrics JSON | Machine-readable routed result | `reports/fpga/integrated_zynq_raw/integrated_zynq_metrics.json` |
| Vendor-snapshot implementation | Hardware-correlated routed result | `reports/fpga/integrated-zynq-snapshot-implementation-summary.md` |
| Vendor-snapshot strategy sweep | Repeat implementation directives and selected timing result | `reports/fpga/integrated-zynq-snapshot-implementation-sweep.md` |
| PS7 provenance artifact | Board clock and DDR settings snapshot | `hardware/7020_ad936x_sdr/ps/bringup_tests/design_1_wrapper/ps7_summary.html` |

## Key results

Placed and routed out of context at 100 MHz with the port paths timed
(`reports/fpga/block5-bpsk-vivado-evidence.md`; the first synthesis-only snapshot is kept in
`reports/fpga/block5-timing-summary.md`):

| Block | LUT | FF | DSP | BRAM | Fmax, MHz | Latency, cycles | Timing result |
|---|---:|---:|---:|---:|---:|---:|---|
| `iq_passthrough` | 1 | 33 | 0 | 0 | 373.134 | 1 | meets 100 MHz with `7.320 ns` WNS |
| `fir_iq_4tap` | 117 | 129 | 4 | 0 | 97.590 | 1 | misses 100 MHz by `0.247 ns` WNS |
| `nco_mixer_iq` | 110 | 43 | 4 | 0 | 96.516 | 1 | misses 100 MHz by `0.361 ns` WNS |
| `axis_iq_passthrough` | 4 | 34 | 0 | 0 | 288.934 | 1 | meets 100 MHz with `6.539 ns` WNS |

## Interpretation

- The two arithmetic blocks remain compact on XC7Z020: both use 4 DSP48E1 slices and no BRAM tiles.
- The AXI-Stream wrapper overhead is negligible compared with the arithmetic blocks, which is useful when estimating integration cost into a Zynq data path.
- `fir_iq_4tap` and `nco_mixer_iq` both miss 100 MHz by a fraction of a nanosecond on the same kind of path: product, sum, rounding and saturation in one clock. Registering the sum before rounding and saturation closes it (Lab 5.2, exercise 4).

## Integrated routed results

The dual-modem overlay has two distinct Vivado flows. The vendor-snapshot flow is the hardware-correlated signoff candidate; the standalone reconstruction remains a diagnostic comparison.

| Flow | LUT | FF | DSP | BRAM | WNS, ns | TNS, ns | Hardware result |
|---|---:|---:|---:|---:|---:|---:|---|
| Standalone recreated | 13,795 | 21,780 | 28 | 4.0 | +0.354 | 0.000 | gpreg alive, sample-path counters stay zero |
| Vendor snapshot, `Performance_ExtraTimingOpt` | 27,649 | 36,224 | 216 | 8.0 | +0.096 | 0.000 | QPSK fabric BER=0 on the selected timing-sweep payload; previous CDC-fixed payload also has 4/4 boot sessions and 13/13 attempts |

Both designs are fully routed with zero routing errors. The standalone flow closes timing but is not hardware-functional after runtime reload. After synchronizing the RX channel-select control into the ADC write domain, the vendor snapshot has zero failing timing endpoints and passes board fabric qualification. A follow-up implementation-strategy sweep completed 6/6 timing-clean runs and promoted `Performance_ExtraTimingOpt`, improving canonical WNS from `+0.003 ns` to `+0.096 ns`. This improves margin for the selected implementation, but repeat-build/seed robustness is still separate evidence.

Rebuild and promote the normalized evidence on Windows with:

```powershell
python tools/generate_integrated_vivado_reports.py --flow standalone --build
python tools/generate_integrated_vivado_reports.py --flow snapshot --build
python tools/run_snapshot_impl_sweep.py --jobs 2
python tools/summarize_snapshot_impl_sweep.py --promote-best
```

Without `--build`, the command republishes reports from an existing completed implementation run.

## Limits of the evidence

- The per-module tables are OOC synthesis results; both integrated packages are placed-and-routed results.
- Port-level input/output timing is intentionally unconstrained in this educational flow.
- The vendor-snapshot result satisfies timing closure and board correlation for the internal QPSK fabric path; AD9361/RF operation is a separate acceptance gate.
- The `+0.096 ns` selected result comes from a single strategy sweep over one synthesized snapshot; repeat-build or seed evidence is still needed before calling timing closure robust.
