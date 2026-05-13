# Demo Lab Flow

This page summarizes the intended hands-on SDR workflow.

## Objective

The goal is to connect theory, implementation and real measurements.

## End-to-end engineering chain

```text
reference model
-> FPGA waveform generation
-> RF transmission
-> independent reception
-> IQ recording
-> offline analysis
-> engineering report
```

## Recommended hardware setup

| Device | Role |
|---|---|
| Zynq-7020 + AD9363 | signal generation and FPGA processing |
| RTL-SDR | independent external receiver |
| HDSDR | visualization and IQ capture |
| MATLAB / Python | offline analysis |

## Suggested student experiment

### Step 1 — Generate waveform

Create a clean reference waveform in software.

### Step 2 — Run FPGA chain

Transmit the waveform using the SDR platform.

### Step 3 — Observe spectrum

Verify:

- carrier frequency;
- bandwidth;
- spurious components;
- gain configuration.

### Step 4 — Record IQ samples

Store IQ captures together with:

- sample rate;
- center frequency;
- gain settings;
- capture timestamp.

### Step 5 — Analyze recording

Evaluate:

- FFT spectrum;
- constellation;
- synchronization quality;
- BER/EVM metrics.

## Educational result

Students should see how a communication system behaves not only in simulation, but also in a real RF experiment.
