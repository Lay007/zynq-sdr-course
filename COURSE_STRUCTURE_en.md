# Course Structure

## Overall logic

The course is structured as an engineering route: from understanding signals and SDR architecture to reproducible experiments, FPGA implementation and a final project.

```mermaid
flowchart TB
    B1["1. Introduction and first RF experiment<br/>SDR concept, setup, software, RTL-SDR and test tone"]
    B2["2. Signals and sampling<br/>spectrum, I/Q, sample rate, aliasing and frequency domain basics"]
    B3["3. DSP fundamentals<br/>FFT, windows, filtering, frequency estimation and mixing"]
    B4["4. Modeling and fixed-point<br/>MATLAB / Simulink, scaling, quantization and HDL preparation"]
    B5["5. HDL / FPGA flow<br/>Verilog/VHDL, Vivado/Vitis, SoC integration and verification"]
    B6["6. RF frontend and AD9363<br/>frequency, levels, bandwidth, filters and measurement safety"]
    B7["7. TX/RX SDR chains<br/>DUC/DDC, generators, pipelines and IQ tap points"]
    B8["8. Modulation and synchronization<br/>BPSK/QPSK/FSK, CFO, timing recovery and demodulation"]
    B9["9. Recording and analysis<br/>HDSDR, MATLAB, Simulink, Python, C++ and GNU Radio"]
    B10["10. KiCad and circuits<br/>breadboard, analog/digital support circuits and measurements"]
    B11["11. Integrated SDR project<br/>full route from model to RF measurement and analysis"]
    B12["12. Final projects<br/>independent extensions and portfolio-level results"]

    B1 --> B2 --> B3 --> B4 --> B5 --> B6 --> B7 --> B8 --> B9 --> B10 --> B11 --> B12
```

## Learning levels

| Level | Focus | Engineering result |
|---|---|---|
| Signal theory | signals, spectrum, sampling, I/Q | student understands what is measured |
| Modeling | MATLAB / Simulink reference | expected behavior is defined |
| Implementation | fixed-point, HDL, FPGA | model is mapped to hardware |
| RF measurement | AD9363, RTL-SDR, levels | physical signal is validated |
| Analysis | IQ replay, FFT, EVM, BER | experiment becomes reproducible |
| Project | full system integration | portfolio-level result |

## Blocks

### Block 1 — Introduction and first reception
Defines the setup, introduces HDSDR/RTL-SDR and performs the first RF experiment.

### Block 2 — Signals and sampling
Explains spectrum, complex representation and aliasing with practical examples.

### Block 3 — DSP basics
Covers FFT, filtering and frequency estimation as SDR building blocks.

### Block 4 — Simulink and fixed-point
Transforms floating-point models into hardware-ready representations.

### Block 5 — FPGA / HDL flow
Introduces HDL, FPGA pipelines and SoC integration.

### Block 6 — RF frontend
Connects digital samples to RF hardware behavior and measurement constraints.

### Block 7 — TX/RX chains
Builds full SDR transmit and receive chains.

### Block 8 — Modulation and synchronization
Adds digital modulation and recovery algorithms.

### Block 9 — Recording and analysis
Standardizes IQ recording and multi-tool analysis.

### Block 10 — KiCad and circuits
Introduces circuit design as part of SDR experiments.

### Block 11 — Integrated project
Combines all layers into a full SDR system.

### Block 12 — Final projects
Defines independent project paths.

## Recommended cadence

1. Theory and engineering context
2. Demonstration
3. Lab with measurements
4. Analysis and conclusions
5. Short reproducible report
