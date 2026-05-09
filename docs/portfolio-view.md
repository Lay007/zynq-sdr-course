# Portfolio View

This page explains what the repository demonstrates from an engineering and hiring perspective.

## What this project demonstrates

| Area | Evidence in the repository |
|---|---|
| DSP | FFT, FIR, mixing, decimation, spectra |
| Fixed-point design | quantization, scaling, saturation, error analysis |
| Verilog / FPGA | RTL blocks, testbenches, AXI-Stream style wrapper |
| RF engineering | frequency plan, gain staging, AD9363 settings |
| SDR systems | TX/RX chain, DUC/DDC, loopback metrics |
| Synchronization | CFO, phase, timing and end-to-end sync chain |
| IQ data engineering | metadata, CI16/CU8/CF32 readers, capture quality checks |
| Electronics | RC filters, attenuators, RF measurement safety, KiCad workflow |
| CI/CD | MkDocs strict build, Python labs, Verilog smoke tests |
| Documentation | bilingual course structure and engineering reports |

## Why it is technically strong

The repository is not just a collection of notes. It contains executable examples, measurable artifacts and CI checks:

- Python scripts generate reproducible plots and metrics;
- Verilog testbenches check RTL behavior;
- metadata-driven IQ readers demonstrate real signal workflow;
- MkDocs builds the course as a navigable site;
- report checklists teach engineering communication.

## Suggested portfolio summary

```text
Bilingual SDR engineering course covering DSP, fixed-point design, Verilog/FPGA flow,
RF frontend setup, TX/RX chains, synchronization, IQ recording analysis and basic electronics.
The repository includes executable labs, generated metrics, CI validation and report templates.
```

## Best pages to show first

1. Course demo dashboard.
2. Model → FPGA → RF → Measurement.
3. Block 8 end-to-end synchronization chain.
4. Block 9 IQ recording and analysis workflow.
5. Block 11 integrated SDR project workflow.

## Skills matrix

| Skill | Level demonstrated |
|---|---|
| Signal-processing modeling | high |
| Fixed-point implementation thinking | high |
| RTL verification | medium/high |
| RF measurement discipline | medium/high |
| Data-analysis reproducibility | high |
| Engineering documentation | high |
| CI automation | medium/high |

## Next proof points

- add real IQ captures through external dataset links;
- add screenshots from actual SDR hardware experiments;
- add a final integrated project report;
- add KiCad source files for the electronics mini-project;
- add measured hardware results next to synthetic baselines.
