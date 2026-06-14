# IQ Demo Dataset Manifest

This page documents the first small dataset contract for QPSK replay and future hardware captures.

## Purpose

The repository should not store large raw IQ files directly. Instead, each dataset has a manifest that explains where the data comes from, how to verify it and which labs use it.

## Demo dataset

| Field | Value |
|---|---|
| Dataset | `demo_qpsk_capture` |
| Manifest | `datasets/demo_qpsk_capture/manifest.yaml` |
| Storage | synthetic or external |
| Intended use | QPSK constellation, EVM/SNR, replay checks |
| Required before hardware claim | checksum, capture settings, RF path, gain values |

## Required files

```text
datasets/demo_qpsk_capture/
  README.md
  manifest.yaml
```

Optional files for future work:

```text
preview_constellation.png
preview_spectrum.png
checksum.txt
download.txt
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
