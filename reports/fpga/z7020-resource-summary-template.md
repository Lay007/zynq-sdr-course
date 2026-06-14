# Z7020 FPGA Resource Summary Template

Use this file as the first board-level summary for Block 5 and Block 11 FPGA-facing work.

## Target

| Field | Value |
|---|---|
| Board | Zynq-7020 SDR board |
| RF module | AD9363 / ADRV-compatible module |
| Tool | Vivado / TBD |
| Clock | TBD |
| Commit | TBD |

## Resource summary

| HDL block | LUT | FF | DSP | BRAM | Fmax, MHz | Latency, cycles | Status |
|---|---:|---:|---:|---:|---:|---:|---|
| `iq_passthrough` | TBD | TBD | TBD | TBD | TBD | TBD | simulation only |
| `fir_iq_4tap` | TBD | TBD | TBD | TBD | TBD | TBD | simulation only |
| `nco_mixer_iq` | TBD | TBD | TBD | TBD | TBD | TBD | simulation only |
| `axis_iq_passthrough` | TBD | TBD | TBD | TBD | TBD | TBD | simulation only |

## Timing notes

- Target clock: TBD.
- Worst negative slack: TBD.
- Timing status: TBD.

## Interpretation

Fill this section after synthesis or implementation. Explain which resource limits matter first for SDR work: DSP slices, BRAM, clock rate, interface bandwidth or development complexity.
