# Block 5 Vivado Utilization Summary

This page summarizes the Vivado 2021.1 out-of-context utilization reports for the four educational HDL blocks from Block 5.

## Run context

| Field | Value |
|---|---|
| Device | `xc7z020clg400-2` |
| Clock context | `FPGA0 = 100.000000 MHz` from `hardware/7020_ad936x_sdr/ps/bringup_tests/design_1_wrapper/ps7_summary.html` |
| Report generator | `python tools/generate_block5_vivado_reports.py` |
| Raw metrics | `reports/fpga/vivado_ooc_raw/block5_vivado_ooc_metrics.json` |

## Module summary

| Block | LUT | FF | DSP | BRAM tiles | Main primitive pattern | Raw report |
|---|---:|---:|---:|---:|---|---|
| `iq_passthrough` | 1 | 33 | 0 | 0 | `FDRE x33`, `LUT2 x1` | `vivado_ooc_raw/iq_passthrough_utilization.rpt` |
| `fir_iq_4tap` | 117 | 129 | 4 | 0 | `FDRE x129`, `DSP48E1 x4`, `CARRY4 x40` | `vivado_ooc_raw/fir_iq_4tap_utilization.rpt` |
| `nco_mixer_iq` | 110 | 37 | 4 | 0 | `FDRE x37`, `DSP48E1 x4`, `CARRY4 x23` | `vivado_ooc_raw/nco_mixer_iq_utilization.rpt` |
| `axis_iq_passthrough` | 5 | 34 | 0 | 0 | `FDRE x34`, `LUT1..LUT6 x1 each` | `vivado_ooc_raw/axis_iq_passthrough_utilization.rpt` |

## Quick reading

- `iq_passthrough` and `axis_iq_passthrough` are effectively interface shells: register-heavy, with negligible LUT cost and no DSP/BRAM consumption.
- `fir_iq_4tap` and `nco_mixer_iq` both infer four DSP48E1 slices, which is expected from their fixed-point multiply-accumulate structure.
- None of the four example blocks consume BRAM in this compact educational implementation.
