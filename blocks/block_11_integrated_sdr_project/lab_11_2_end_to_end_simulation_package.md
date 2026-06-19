# Lab 11.2 — End-to-End Simulation Package

## Goal

Create a reproducible simulation package that connects the signal model, impairments, synchronization and metrics into one executable flow.

## Engineering question

> Can another engineer reproduce the complete simulation and obtain the same figures and metrics?

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
