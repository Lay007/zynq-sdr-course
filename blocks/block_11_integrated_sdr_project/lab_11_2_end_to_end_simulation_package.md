# Lab 11.2 — End-to-End Simulation Package

## Goal

Create a reproducible simulation package that connects the signal model, impairments, synchronization and metrics into one executable flow.

## Engineering question

> Can another engineer reproduce the complete simulation and obtain the same figures and metrics?

## Why this lab matters

A simulation that only its author can run is a demonstration, not evidence. The value of the
package is that a second person, on another machine, gets the same figures and the same
numbers from one command, and can prove it by comparing a checksum. That is also what later
lets a hardware result be compared against a model, stage by stage.

## Package structure

```text
simulation/
  config.json
  run.py
  results/
    figures/
    metrics.json
    summary.md
```

## Required simulation stages

| Stage | Output |
|---|---|
| TX signal generation | symbols or waveform |
| Channel / impairments | noisy and shifted signal |
| RX correction | synchronized signal |
| Metrics | EVM/BER/SNR |
| Report artifacts | plots and JSON |

## Recommended reuse

The final project can reuse existing executable labs:

- Block 7 TX/RX loopback metrics;
- Block 8 end-to-end sync chain;
- Block 9 IQ analysis.

## Current executable reference

The current recommended package for the first modem route is:

| File | Role |
|---|---|
| `blocks/block_11_integrated_sdr_project/python/end_to_end_bpsk_reference.py` | deterministic BPSK package generator |
| `blocks/block_11_integrated_sdr_project/assets/end_to_end_bpsk_reference/` | shared handoff for MATLAB, Simulink and HDL |
| `blocks/block_11_integrated_sdr_project/matlab/end_to_end_bpsk_reference.m` | MATLAB mirror of the package |
| `blocks/block_05_fpga_hdl_flow/rtl/bpsk_symbol_mapper.v` | first RTL anchor for the same bit stream |

Run from the repository root:

```bash
python blocks/block_11_integrated_sdr_project/python/end_to_end_bpsk_reference.py
```

This package already exports Q1.15 symbols and RRC taps, so it can be used as the bridge into Simulink fixed-point and the first Verilog block.

## What to expect

The reference generator is fully deterministic. Running it prints the paths it wrote and
stores its summary in `docs/assets/end_to_end_bpsk_reference_metrics.json`, which for the
committed configuration contains:

| Quantity | Value |
|---|---|
| Frame | 281 bits (25 preamble + 256 payload), 8 samples per symbol at 1 MS/s (125 kSym/s) |
| Injected impairments | 2-sample timing offset, 650 Hz frequency offset, 0.31 rad phase offset |
| RRC filter | 65 taps |
| Payload BER / total BER | 0 / 0 (0 errors) |
| EVM | 2.15 % |
| Peak / RMS level | -1.6 dBFS / -7.3 dBFS |
| Capture SHA-256 | `8b2121ee3fc3946a0064cfd2cc5b5a70eb0813a36937ce82485f91a3f425f113` |

Two habits to take from this: **compare the SHA-256** of your regenerated capture with the
one above (a different hash on the same seed means the environment, not the science,
changed), and note that the **peak is only 1.6 dB below full scale**, so this reference already
sits close to the clipping limit a real ADC would impose.

## Report checklist

- [ ] Provide a run command.
- [ ] Provide config file.
- [ ] Save generated figures.
- [ ] Save metrics JSON.
- [ ] Explain all random seeds.
- [ ] State pass/fail criteria.

## Engineering conclusion template

```text
The simulation package can be reproduced with command ______. It generates figures ______ and metrics ______.
The resulting EVM is ____ %, BER is ____ and SNR is ____ dB.
```
