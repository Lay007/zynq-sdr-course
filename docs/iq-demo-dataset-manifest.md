# IQ Demo Dataset Manifest

This page documents the first small dataset contract for QPSK replay and future hardware captures.

## Purpose

The repository should not store large raw IQ files directly. Instead, each dataset has a manifest that explains where the data comes from, how to verify it and which labs use it.

## Demo dataset

| Field | Value |
|---|---|
| Dataset | `demo_qpsk_capture` |
| Manifest | `datasets/demo_qpsk_capture/manifest.yaml` |
| Storage | Git LFS, 64 KiB CI16 |
| Publication status | synthetic-public |
| Intended use | QPSK constellation, BER/SER, EVM/SNR, replay checks |
| Provenance | deterministic generator, seed `7020`, SHA256 in manifest |

## Required files

```text
datasets/demo_qpsk_capture/
  README.md
  demo_qpsk_capture.ci16
  manifest.yaml
  metrics.json
  analysis_summary.json
```

Report-ready previews:

```text
docs/assets/demo_qpsk_constellation.svg
docs/assets/demo_qpsk_spectrum.svg
```

## Acceptance criteria

A dataset is usable in the course when:

- sample rate is known;
- IQ format is known;
- center frequency or baseband reference is documented;
- checksum is available for real captures;
- access policy is clear;
- at least one analysis command is listed;
- expected metrics are defined.

This fixture does not replace the local measured OTA QPSK WAV. It supplies a publication-safe replay baseline; the measured capture remains hardware evidence until its raw-data publication review is complete.
