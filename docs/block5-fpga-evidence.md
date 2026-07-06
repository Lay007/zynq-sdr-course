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

## Integrated routed result

The current dual-modem Zynq overlay was also built through synthesis, placement, routing and bitstream generation with Vivado 2021.1 for `xc7z020clg400-2`.

| LUT | FF | DSP | BRAM tiles | WNS, ns | TNS, ns | Routing errors |
|---:|---:|---:|---:|---:|---:|---:|
| 13,795 | 21,780 | 28 | 4.0 | 0.354 | 0.000 | 0 |

All 29,899 routable nets are fully routed and all 48,851 timing endpoints pass. The report generator rejects missing metrics, routing errors and timing failure instead of publishing a partial success.

Rebuild and promote the normalized evidence on Windows with:

```powershell
python tools/generate_integrated_vivado_reports.py --build
```

Without `--build`, the command republishes reports from an existing completed implementation run.

## Limits of the evidence

- The per-module tables are OOC synthesis results; the separate integrated package is a placed-and-routed top-level result.
- Port-level input/output timing is intentionally unconstrained in this educational flow.
- Successful implementation does not prove AD9361 calibration, RF quality or repeatable clean-boot board operation.
