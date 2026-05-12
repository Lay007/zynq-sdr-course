# Reproducible Engineering Route

The course is intentionally structured as a reproducible engineering flow.

## Core idea

A signal-processing project should not stop at a simulation screenshot.

The engineering route should connect:

```text
signal theory
-> software model
-> fixed-point constraints
-> FPGA implementation
-> RF experiment
-> measurement
-> report
```

## Why this matters

Many educational SDR repositories demonstrate only one layer:

- only MATLAB;
- only GNU Radio;
- only HDL;
- only hardware screenshots.

This course instead tries to connect all layers into one consistent workflow.

## Recommended student workflow

### Stage 1 — Reference model

Build the cleanest possible software reference.

### Stage 2 — Quantization and fixed-point

Introduce implementation constraints:

- limited precision;
- scaling;
- saturation;
- overflow visibility.

### Stage 3 — HDL / FPGA

Translate stable DSP blocks into streaming RTL.

### Stage 4 — RF experiment

Transmit and receive a real waveform.

### Stage 5 — Measurement

Evaluate:

- spectrum;
- constellation;
- EVM;
- BER;
- synchronization quality.

### Stage 6 — Engineering report

Document:

- assumptions;
- configuration;
- metrics;
- plots;
- reproducibility steps.

## Educational objective

The goal is to teach students how communication systems are engineered and validated in practice, not only how they are simulated.
