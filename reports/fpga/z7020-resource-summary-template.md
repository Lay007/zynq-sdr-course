# Z7020 FPGA Resource Summary

This file is the board-level FPGA summary for the first Block 5 Vivado OOC evidence package.

## Target

| Field | Value |
|---|---|
| Board | Zynq-7020 SDR board |
| RF module | AD9363 / ADRV-compatible module |
| Device | `xc7z020clg400-2` |
| Tool | Vivado 2021.1 OOC synthesis |
| PS reference clock | `33.333333 MHz` from `ps7_summary.html` |
| PL clock used for Block 5 reports | `FPGA0 = 100.000000 MHz` from `ps7_summary.html` |
| DDR operating frequency | `533.333 MHz` from `ps7_summary.html` |
| Source RTL commit | `ad2936c` |
| Report generator | `python tools/generate_block5_vivado_reports.py` |
| Raw PS7 artifact | `hardware/7020_ad936x_sdr/ps/bringup_tests/design_1_wrapper/ps7_summary.html` |
| Raw Vivado metrics | `reports/fpga/vivado_ooc_raw/block5_vivado_ooc_metrics.json` |

## Resource summary

| HDL block | LUT | FF | DSP | BRAM | Fmax, MHz | Latency, cycles | Status |
|---|---:|---:|---:|---:|---:|---:|---|
| `iq_passthrough` | 1 | 33 | 0 | 0 | see timing summary | see latency notes | Vivado OOC synthesized |
| `fir_iq_4tap` | 117 | 129 | 4 | 0 | see timing summary | see latency notes | Vivado OOC synthesized |
| `nco_mixer_iq` | 110 | 37 | 4 | 0 | see timing summary | see latency notes | Vivado OOC synthesized |
| `axis_iq_passthrough` | 5 | 34 | 0 | 0 | see timing summary | see latency notes | Vivado OOC synthesized |

## Timing notes

- Target clock and WNS/TNS details are recorded in the dedicated timing summary.
- These values come from Vivado out-of-context synthesis, not from a placed-and-routed full board design.

## Interpretation

- The two arithmetic blocks are already small on XC7Z020: both `fir_iq_4tap` and `nco_mixer_iq` stay at 4 DSP48E1 slices and 0 BRAM tiles.
- The passthrough wrappers are effectively control/register shells, which makes them useful baselines for AXI-Stream integration overhead.
