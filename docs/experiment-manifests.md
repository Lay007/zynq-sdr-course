# Experiment Manifests

Experiment manifests connect course labs with reproducible engineering evidence.

They are stored in the repository-level `experiments/` directory and describe:

- engineering objective;
- signal configuration;
- expected plots and reports;
- required capture metadata;
- acceptance criteria.

## Current manifests

| Lab | Manifest | Engineering output |
|---|---|---|
| Lab 1 | [lab01_tone_rf_iq.yaml](https://github.com/Lay007/zynq-sdr-course/blob/main/experiments/lab01_tone_rf_iq.yaml) | Tone → RF observation → IQ analysis |
| Lab 3 | [lab03_qpsk_constellation.yaml](https://github.com/Lay007/zynq-sdr-course/blob/main/experiments/lab03_qpsk_constellation.yaml) | QPSK constellation and EVM/SNR visibility |
| Lab 5 | [lab05_fir_rtl.yaml](https://github.com/Lay007/zynq-sdr-course/blob/main/experiments/lab05_fir_rtl.yaml) | FIR RTL mapping and streaming testbench validation |
| Lab 6 | [lab06_rf_frontend.yaml](https://github.com/Lay007/zynq-sdr-course/blob/main/experiments/lab06_rf_frontend.yaml) | RF frontend configuration and gain staging |
| Lab 8 | [lab08_sync_chain.yaml](https://github.com/Lay007/zynq-sdr-course/blob/main/experiments/lab08_sync_chain.yaml) | CFO/phase/timing correction and BER/EVM comparison |
| Lab 9 | [lab09_iq_recording.yaml](https://github.com/Lay007/zynq-sdr-course/blob/main/experiments/lab09_iq_recording.yaml) | IQ recording, metadata and replay analysis |
| Lab 11 | [lab11_integrated_sdr_project.yaml](https://github.com/Lay007/zynq-sdr-course/blob/main/experiments/lab11_integrated_sdr_project.yaml) | Integrated SDR project validation |
| Lab 5.5 | [lab55_float_fixed_rtl_comparison.yaml](https://github.com/Lay007/zynq-sdr-course/blob/main/experiments/lab55_float_fixed_rtl_comparison.yaml) | Numeric consistency: float vs fixed vs RTL |
| Lab 6.5 | [lab65_rf_impairment_calibration.yaml](https://github.com/Lay007/zynq-sdr-course/blob/main/experiments/lab65_rf_impairment_calibration.yaml) | RF impairment calibration before/after metrics |
| Lab 7.4 | [lab74_packet_receiver_detection.yaml](https://github.com/Lay007/zynq-sdr-course/blob/main/experiments/lab74_packet_receiver_detection.yaml) | Packet detection reliability and timing error |
| Lab 8.5 | [lab85_ofdm_mini_link.yaml](https://github.com/Lay007/zynq-sdr-course/blob/main/experiments/lab85_ofdm_mini_link.yaml) | OFDM sync/equalization BER/EVM validation |
| Lab 8.6 | [lab86_channel_coding_ber_comparison.yaml](https://github.com/Lay007/zynq-sdr-course/blob/main/experiments/lab86_channel_coding_ber_comparison.yaml) | BER-vs-SNR coding and interleaving comparison |
| Lab 11.5 | [lab115_axi_dma_latency_jitter.yaml](https://github.com/Lay007/zynq-sdr-course/blob/main/experiments/lab115_axi_dma_latency_jitter.yaml) | Runtime latency/jitter/throughput model |
| Lab 11.6 | [lab116_measurement_uncertainty_budget.yaml](https://github.com/Lay007/zynq-sdr-course/blob/main/experiments/lab116_measurement_uncertainty_budget.yaml) | Type A/Type B uncertainty budget reporting |

## How to use a manifest

1. Open the corresponding lab page.
2. Review the manifest before running the experiment.
3. Record all required metadata.
4. Generate the expected plots.
5. Complete the report template.
6. Check the acceptance criteria.

## Validation

Run the manifest checker locally:

```bash
python tools/check_experiment_manifests.py
```

The GitHub Actions workflow `.github/workflows/experiment-manifests-check.yml` validates manifest structure on push and pull requests.

## Manifest-driven course design

A lab should not be considered complete only because the text exists.

A mature lab should include:

| Evidence | Purpose |
|---|---|
| Lab page | explains the theory and workflow |
| Script or procedure | makes the result repeatable |
| Manifest | documents configuration and expectations |
| Generated figure | shows observable behavior |
| Report template | turns data into engineering conclusions |
| CI or checklist | prevents silent regressions |

## Planned extensions

- add manifests for all hardware-oriented labs;
- validate generated artifact paths in CI;
- connect manifests to generated reports;
- provide a final-project manifest template.
