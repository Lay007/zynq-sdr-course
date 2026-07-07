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
| Latency and throughput notes | One-cycle pipeline and streaming behaviour | `reports/fpga/block5-latency-throughput-notes.md` |
| Raw metrics JSON | Machine-readable run summary | `reports/fpga/vivado_ooc_raw/block5_vivado_ooc_metrics.json` |
| Integrated implementation summary | Placed-and-routed top-level result | `reports/fpga/integrated-zynq-implementation-summary.md` |
| Integrated metrics JSON | Machine-readable routed result | `reports/fpga/integrated_zynq_raw/integrated_zynq_metrics.json` |
| Vendor-snapshot implementation | Hardware-correlated routed result | `reports/fpga/integrated-zynq-snapshot-implementation-summary.md` |
| PS7 provenance artifact | Board clock and DDR settings snapshot | `hardware/7020_ad936x_sdr/ps/bringup_tests/design_1_wrapper/ps7_summary.html` |

## Key results

| Block | LUT | FF | DSP | BRAM | Fmax, MHz | Latency, cycles | Timing result |
|---|---:|---:|---:|---:|---:|---:|---|
| `iq_passthrough` | 1 | 33 | 0 | 0 | N/A | 1 | no internal reg-to-reg setup path in OOC timing |
| `fir_iq_4tap` | 117 | 129 | 4 | 0 | 98.795 | 1 | misses 100 MHz by `0.125 ns` WNS |
| `nco_mixer_iq` | 110 | 37 | 4 | 0 | 92.558 | 1 | misses 100 MHz by `0.807 ns` WNS |
| `axis_iq_passthrough` | 5 | 34 | 0 | 0 | 579.710 | 1 | meets 100 MHz with `8.064 ns` WNS |

## Interpretation

- The two arithmetic blocks remain compact on XC7Z020: both use 4 DSP48E1 slices and no BRAM tiles.
- The AXI-Stream wrapper overhead is negligible compared with the arithmetic blocks, which is useful when estimating integration cost into a Zynq data path.
- `fir_iq_4tap` is already close to the 100 MHz target, while `nco_mixer_iq` needs additional timing headroom before it should be treated as an integrated board-level datapath block.

## Integrated routed results

The dual-modem overlay has two distinct Vivado flows. The vendor-snapshot flow is the hardware-correlated signoff candidate; the standalone reconstruction remains a diagnostic comparison.

| Flow | LUT | FF | DSP | BRAM | WNS, ns | TNS, ns | Hardware result |
|---|---:|---:|---:|---:|---:|---:|---|
| Standalone recreated | 13,795 | 21,780 | 28 | 4.0 | +0.354 | 0.000 | gpreg alive, sample-path counters stay zero |
| Vendor snapshot | 27,597 | 36,169 | 216 | 8.0 | +0.003 | 0.000 | QPSK fabric BER=0, 4/4 boot sessions and 13/13 attempts on the timing-clean payload |

Both designs are fully routed with zero routing errors. The standalone flow closes timing but is not hardware-functional after runtime reload. After synchronizing the RX channel-select control into the ADC write domain, the vendor snapshot has zero failing timing endpoints and the same payload passes repeated board qualification. Its WNS is only `+0.003 ns`, so repeat-build/seed margin remains an engineering improvement rather than an open functional signoff gate.

Rebuild and promote the normalized evidence on Windows with:

```powershell
python tools/generate_integrated_vivado_reports.py --flow standalone --build
python tools/generate_integrated_vivado_reports.py --flow snapshot --build
```

Without `--build`, the command republishes reports from an existing completed implementation run.

## Limits of the evidence

- The per-module tables are OOC synthesis results; both integrated packages are placed-and-routed results.
- Port-level input/output timing is intentionally unconstrained in this educational flow.
- The vendor-snapshot result satisfies timing closure and board correlation for the internal QPSK fabric path; AD9361/RF operation is a separate acceptance gate.
- Timing margin is only `+0.003 ns`; a repeat-build or seed sweep is needed before calling the closure robust.
