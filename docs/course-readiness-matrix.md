# Course Readiness Matrix

This matrix helps track whether the course is only documented or truly reproducible.

## Readiness levels

| Level | Meaning |
|---|---|
| L0 | topic exists |
| L1 | documentation exists |
| L2 | runnable example exists |
| L3 | generated figure or report exists |
| L4 | CI or checklist validates the result |
| L5 | hardware or measurement path is documented |

## Course blocks

| Block | Topic | Target readiness | Main evidence |
|---|---|---:|---|
| 01 | SDR introduction | L3 | overview, figures, learning route |
| 02 | Signals and sampling | L3 | executable plots and explanations |
| 03 | DSP basics | L4 | Python/MATLAB labs and generated plots |
| 04 | Simulink and fixed-point | L3 | fixed-point workflow and lab outputs |
| 05 | FPGA / HDL flow | L4 | Verilog testbenches and smoke checks |
| 06 | RF frontend and AD9363 | L5 | hardware configuration and RF notes |
| 07 | TX/RX chains | L4 | DUC/DDC and loopback metrics |
| 08 | Modulation and synchronization | L4 | CFO, phase, timing and BER/EVM labs |
| 09 | IQ recording and analysis | L5 | metadata, file formats and replay path |
| 10 | Electronics and KiCad | L3 | safety checklist and schematic tasks |
| 11 | Integrated SDR project | L5 | report template and validation path |
| 12 | Final projects | L5 | portfolio-ready project outputs |

## Improvement priorities

1. Keep every lab connected to a generated figure or report.
2. Add metadata for every real or synthetic capture.
3. Keep hardware bring-up steps explicit.
4. Ensure CI validates the most important examples.
5. Use one visual style for all generated figures.
