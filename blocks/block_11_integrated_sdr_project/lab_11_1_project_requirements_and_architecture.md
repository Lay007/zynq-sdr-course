# Lab 11.1 — Project Requirements and System Architecture

## Goal

Define the final SDR project requirements and convert them into a clear system architecture.

## Engineering question

> What exactly should the integrated SDR project do, and which blocks are required to prove that it works?

## Required decisions

| Decision | Description |
|---|---|
| Signal type | tone, QPSK, packet, custom waveform |
| Sample-rate plan | model rate, FPGA rate, RF capture rate |
| Frequency plan | TX LO, RX LO, digital offsets |
| Implementation scope | Python/MATLAB, fixed-point, RTL, RF |
| Metrics | FFT peak, SNR, EVM, BER |
| Success criteria | numeric pass/fail thresholds |

## Reference architecture

```mermaid
flowchart LR
    SRC[Signal source] --> DSP[DSP model]
    DSP --> FXP[Fixed-point model]
    FXP --> RTL[RTL block]
    RTL --> RF[RF frontend]
    RF --> IQ[IQ recording]
    IQ --> RX[RX processing]
    RX --> METRICS[Metrics]
```

## Report checklist

- [ ] State project goal.
- [ ] Define success criteria.
- [ ] Draw system architecture.
- [ ] Define sample-rate plan.
- [ ] Define frequency plan.
- [ ] Define data formats.
- [ ] Define metrics and thresholds.
- [ ] State project risks.

## Engineering conclusion template

```text
The integrated SDR project targets ______. The main signal chain is ______.
The project is considered successful if ______. The highest technical risk is ______ because ______.
```
