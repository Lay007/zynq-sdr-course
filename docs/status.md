# Course status and readiness matrix

This page is the compact top-level engineering status board for the course. It shows what is already strong, what is executable, and what still needs hardware validation.

Detailed bring-up logs should live on dedicated evidence pages rather than inside this matrix.

## Readiness legend

| Mark | Meaning |
|---|---|
| `Ready` | Stable learner-facing material. |
| `Executable` | Scripts, tests, plots or reproducible checks exist. |
| `Measured` | Real hardware or IQ capture evidence exists. |
| `Hardware pending` | Board-level validation or real capture data is still needed. |
| `Portfolio-ready` | Documentation, reproducible artifacts and reviewer-friendly evidence are present. |

## Quick decodings

| Term | Meaning here |
|---|---|
| `stock-shell` | The board's normal vendor Linux and PL baseline after boot. |
| `runtime overlay` | A PL payload loaded after Linux boot for course experiments. |
| `BPSK` | Binary phase-shift keying. |
| `evidence` | A manifest, JSON report, plot or log proving the result. |

## Block readiness matrix

| Block | Topic | Current state | Evidence level | Main gap / next improvement |
|---|---|---|---|---|
| 01 | Intro to SDR | Ready | Real RTL-SDR captures and controlled Zynq tone witness | Add a short learner report comparing passive capture and controlled tone. |
| 02 | Signals and sampling | Executable | Python labs and generated figures | Add MATLAB/C++ translations and metadata-mistake replay examples. |
| 03 | DSP basics | Executable | Python / MATLAB / C++ path | Add direct-vs-FFT convolution threshold demo and more reference outputs. |
| 04 | Simulink and fixed-point | Executable | Python/MATLAB references and BPSK `.slx` models | Constrain the BPSK Simulink path further for HDL Coder handoff. |
| 05 | FPGA / HDL flow | Executable | Verilog testbenches, HDL CI, timing-clean BPSK BER baseline | Replace the coarse acquisition prefix with a more selective timing-safe detector and promote routed reports. |
| 06 | RF frontend and AD9363 | Measured | RX-only and tone capture baselines | Build the AD9363 gain table and validate safe cabled loopback. |
| 07 | TX/RX chains | Executable | DUC/DDC demos and loopback models | Add measurement package. |
| 08 | Modulation and synchronization | Executable | CFO, phase/timing, BER/EVM demos and SNR-vs-BER trap material | Promote generated impairment dashboards and connect them to measured Block 11 reports. |
| 09 | Recording and analysis tools | Executable | CI16/CU8/CF32 readers and recording CI | Update QPSK dataset manifest with real checksum or synthetic generator. |
| 10 | KiCad and basic electronics | Draft | Calculators and templates | Add measured breadboard photos and KiCad exports. |
| 11 | Integrated SDR project | On-chip BER=0 (loopback) | On-chip PL BPSK BER=0 (received=281, total_errors=0) via gap-free TX + 8-bit frame-sync; TX/RX raw-sample tap + RTL-SDR evidence | Deterministic per-burst BER=0 via multi-phase diversity RX (model-verified); then a QPSK modem and a final report. |
| 12 | Final projects | Draft | Templates, rubric and example skeleton | Fill one complete portfolio-ready final project report. |

## Hardware validation priorities

| Priority | Task | Done when |
|---|---|---|
| P0 | Safe cabled loopback | Attenuation, gain settings, capture metadata and short conclusion are recorded. |
| P0 | Runtime PL BPSK robustness | External monitor BER is repeatable from clean boot and reported with limitations. |
| P1 | QPSK demo dataset | Manifest, checksum or immutable link, constellation, EVM/SNR and replay command exist. |
| P1 | Digital-link metric gate | Digital labs report SNR/EVM plus BER or FER with compared bit/frame count. |
| P1 | AD9363 gain table | Gain settings, clipping/SNR behavior and safe starting values are documented. |
| P2 | Final hardware report | One report connects model, HDL, capture, metrics and engineering conclusion. |

## Evidence and backlog pages

- [Hardware evidence index](hardware-evidence-index.md)
- [Hardware validation backlog](hardware-validation-backlog.md)
- [Block 11 hardware bring-up summary](block11-hardware-bringup-summary.md)
- [Reviewer acceptance checklist](reviewer-checklist.md)
- [Course quality roadmap](course-quality-roadmap.md)
- [Release checklist](release-checklist.md)

## Current release focus

The next public milestone should be `v0.1.0`: a reviewed, reproducible course snapshot with a clean learner route, green CI, compact status pages and one flagship model-to-measurement hardware story.
