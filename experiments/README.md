# Experiment Manifests

This directory contains reproducible experiment manifests for the Zynq SDR Course.

The manifests describe the engineering intent, expected outputs, required metadata and acceptance criteria for selected labs.

## Available manifests

| Manifest | Purpose |
|---|---|
| `lab01_tone_rf_iq.yaml` | Tone generation, RF observation and IQ analysis |
| `lab03_qpsk_constellation.yaml` | QPSK constellation generation and EVM/SNR analysis |
| `lab08_sync_chain.yaml` | End-to-end synchronization chain with CFO, phase and timing correction |

## Why manifests matter

Each manifest makes a lab easier to reproduce by documenting:

- signal configuration;
- expected plots;
- required metadata;
- acceptance criteria;
- report template;
- hardware/software assumptions.

## Recommended workflow

```text
read lab page
-> inspect experiment manifest
-> run scripts or hardware procedure
-> generate plots
-> complete report template
-> compare with acceptance criteria
```

## Future manifests

Planned additions:

- Lab 5 FPGA FIR verification;
- Lab 6 RF frontend configuration;
- Lab 9 IQ recording and replay;
- Lab 11 integrated SDR project;
- Block 12 final project manifests.
