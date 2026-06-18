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
| `iq_passthrough` | 1 | 33 | 0 | 0 | N/A | 1 | one-cycle valid-only register stage |
| `fir_iq_4tap` | 117 | 129 | 4 | 0 | 98.795 | 1 | one sample/clock, near 100 MHz but needs small timing margin |
| `nco_mixer_iq` | 110 | 37 | 4 | 0 | 92.558 | 1 | one sample/clock, compact mixer needs extra timing headroom |
| `axis_iq_passthrough` | 5 | 34 | 0 | 0 | 579.710 | 1 | one AXIS beat/clock when `tready` stays high |

## Timing notes

- Target clock: `10.000 ns` / `100.000 MHz`, matched to `FPGA0 = 100.000000 MHz` in `ps7_summary.html`.
- Detailed WNS/TNS/data-path values are recorded in `reports/fpga/block5-timing-summary.md`.
- These values come from Vivado out-of-context synthesis, not from a placed-and-routed full board design.

## Interpretation

- The two arithmetic blocks are already small on XC7Z020: both `fir_iq_4tap` and `nco_mixer_iq` stay at 4 DSP48E1 slices and 0 BRAM tiles, which is acceptable for educational SDR baseband chains.
- The passthrough wrappers are effectively control/register shells, which makes them useful baselines for AXI-Stream integration overhead before adding heavier DSP.
- `fir_iq_4tap` is essentially at the 100 MHz line and `nco_mixer_iq` is slightly below it in this compact form, so a real Zynq streaming design should plan for extra pipeline registers or DSP register usage before scaling the chain.
