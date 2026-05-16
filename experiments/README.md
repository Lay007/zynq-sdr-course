# Experiment Manifests

This directory contains reproducible experiment manifests for the Zynq SDR Course.

The manifests describe the engineering intent, expected outputs, required metadata and acceptance criteria for selected labs.

## Available manifests

| Manifest | Purpose |
|---|---|
| `lab01_tone_rf_iq.yaml` | Tone generation, RF observation and IQ analysis |
| `lab03_qpsk_constellation.yaml` | QPSK constellation generation and EVM/SNR analysis |
| `lab05_fir_rtl.yaml` | FIR RTL mapping and streaming testbench validation |
| `lab06_rf_frontend.yaml` | RF frontend configuration and gain staging |
| `lab08_sync_chain.yaml` | End-to-end synchronization chain with CFO, phase and timing correction |
| `lab09_iq_recording.yaml` | IQ recording, metadata and replay analysis |
| `lab11_integrated_sdr_project.yaml` | Integrated SDR project validation |

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

## Validation

Manifests are checked by:

```bash
python tools/check_experiment_manifests.py
```

The GitHub Actions workflow `.github/workflows/experiment-manifests-check.yml` runs this check on push and pull requests.

## Future manifests

Planned additions:

- Lab 7 TX/RX loopback metrics;
- Block 10 electronics/RF safety manifests;
- Block 12 final project manifests.
