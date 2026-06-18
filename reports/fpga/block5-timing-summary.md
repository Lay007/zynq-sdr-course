# Block 5 Timing Summary

This page records the first Vivado timing evidence for the four educational Block 5 RTL modules.

## Constraint and provenance

| Field | Value |
|---|---|
| Device | `xc7z020clg400-2` |
| Target clock | `10.000 ns` period / `100.000 MHz` |
| Clock provenance | `FPGA0 = 100.000000 MHz` in `hardware/7020_ad936x_sdr/ps/bringup_tests/design_1_wrapper/ps7_summary.html` |
| Constraints | `reports/fpga/vivado_ooc_raw/*.xdc` |
| Raw timing reports | `reports/fpga/vivado_ooc_raw/*_timing_summary.rpt` |

## Timing results

| Block | WNS, ns | TNS, ns | Data path delay, ns | Logic levels | Fmax estimate, MHz | Outcome | Raw report |
|---|---:|---:|---:|---:|---:|---|---|
| `iq_passthrough` | N/A | N/A | N/A | N/A | N/A | no internal reg-to-reg setup path in OOC timing | `vivado_ooc_raw/iq_passthrough_timing_summary.rpt` |
| `fir_iq_4tap` | -0.125 | -1.865 | 10.122 | 20 | 98.795 | misses 100 MHz by a narrow margin | `vivado_ooc_raw/fir_iq_4tap_timing_summary.rpt` |
| `nco_mixer_iq` | -0.807 | -11.845 | 10.804 | 15 | 92.558 | misses 100 MHz in current compact implementation | `vivado_ooc_raw/nco_mixer_iq_timing_summary.rpt` |
| `axis_iq_passthrough` | 8.064 | 0.000 | 1.725 | 1 | 579.710 | comfortably meets 100 MHz | `vivado_ooc_raw/axis_iq_passthrough_timing_summary.rpt` |

## OOC caveats

- These reports come from Vivado out-of-context synthesis, not from full implementation in a board design.
- Vivado still reports missing input/output delay constraints for the top-level ports, which is expected for this educational OOC flow.
- Vivado also warns that `HD.CLK_SRC` is unset on the OOC clock port, so clock insertion/skew estimation is incomplete until the modules are placed in a real top-level design.
