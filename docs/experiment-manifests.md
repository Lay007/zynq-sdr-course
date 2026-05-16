# Experiment Manifests

Experiment manifests connect course labs with reproducible engineering evidence.

They are stored in [`../experiments/`](../experiments/) and describe:

- engineering objective;
- signal configuration;
- expected plots and reports;
- required capture metadata;
- acceptance criteria.

## Current manifests

| Lab | Manifest | Engineering output |
|---|---|---|
| Lab 1 | [`lab01_tone_rf_iq.yaml`](../experiments/lab01_tone_rf_iq.yaml) | Tone → RF observation → IQ analysis |
| Lab 3 | [`lab03_qpsk_constellation.yaml`](../experiments/lab03_qpsk_constellation.yaml) | QPSK constellation and EVM/SNR visibility |
| Lab 5 | [`lab05_fir_rtl.yaml`](../experiments/lab05_fir_rtl.yaml) | FIR RTL mapping and streaming testbench validation |
| Lab 6 | [`lab06_rf_frontend.yaml`](../experiments/lab06_rf_frontend.yaml) | RF frontend configuration and gain staging |
| Lab 8 | [`lab08_sync_chain.yaml`](../experiments/lab08_sync_chain.yaml) | CFO/phase/timing correction and BER/EVM comparison |
| Lab 9 | [`lab09_iq_recording.yaml`](../experiments/lab09_iq_recording.yaml) | IQ recording, metadata and replay analysis |
| Lab 11 | [`lab11_integrated_sdr_project.yaml`](../experiments/lab11_integrated_sdr_project.yaml) | Integrated SDR project validation |

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
