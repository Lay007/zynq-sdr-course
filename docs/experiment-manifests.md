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
| Lab 8 | [`lab08_sync_chain.yaml`](../experiments/lab08_sync_chain.yaml) | CFO/phase/timing correction and BER/EVM comparison |

## How to use a manifest

1. Open the corresponding lab page.
2. Review the manifest before running the experiment.
3. Record all required metadata.
4. Generate the expected plots.
5. Complete the report template.
6. Check the acceptance criteria.

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
- validate manifest paths in CI;
- connect manifests to generated reports;
- provide a final-project manifest template.
