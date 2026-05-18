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
| `lab07_tx_rx_loopback.yaml` | TX/RX loopback scenario and quantitative metrics |
| `lab08_sync_chain.yaml` | End-to-end synchronization chain with CFO, phase and timing correction |
| `lab09_iq_recording.yaml` | IQ recording, metadata and replay analysis |
| `lab10_rf_safety_kicad.yaml` | RF safety workflow and KiCad mini-project evidence |
| `lab11_integrated_sdr_project.yaml` | Integrated SDR project validation |
| `lab55_float_fixed_rtl_comparison.yaml` | Numeric consistency between float, fixed and RTL FIR flows |
| `lab65_rf_impairment_calibration.yaml` | Calibration of DC offset, IQ mismatch and LO leakage |
| `lab74_packet_receiver_detection.yaml` | Packet preamble detection reliability metrics |
| `lab85_ofdm_mini_link.yaml` | OFDM mini link with synchronization and equalization |
| `lab86_channel_coding_ber_comparison.yaml` | BER-vs-SNR comparison for coding and interleaving |
| `lab115_axi_dma_latency_jitter.yaml` | AXI DMA runtime latency/jitter model |
| `lab116_measurement_uncertainty_budget.yaml` | Uncertainty budget and engineering reporting |

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

- Block 12 final project manifests.
