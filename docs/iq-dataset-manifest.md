# IQ dataset manifest guide

Real IQ recordings are valuable, but they can easily make a repository large, ambiguous and non-reproducible. This guide defines how the course describes IQ captures without forcing large binary files into Git history.

## Recommended policy

- Keep small synthetic demo files in the repository only when they are tiny and useful for tests.
- Store real captures externally or through Git LFS when needed.
- Always provide a manifest file with metadata, checksums and analysis intent.
- Do not publish captures with unclear spectrum origin, unknown frequency, or missing sample format.
- Prefer reproducible synthetic examples for CI and public documentation.

## Manifest kinds

The checker distinguishes three contracts. Use `manifest_kind` explicitly for new files; older captures are classified from `storage` and the filename for compatibility.

| Kind | Purpose | Required evidence |
|---|---|---|
| `dataset` | Fixed, reproducible input intended for replay or sharing | version, status, file reference, SHA256 when fixed, source, analysis targets, quality checks and license |
| `capture-session` | Local bench result whose raw file is not yet published | local/repository file hint, capture settings, analysis command, signal description and notes |
| `template` | Intentionally incomplete form for a future capture | all canonical top-level fields may contain null or placeholder values while `status: template` |

New manifests start with:

```yaml
manifest_kind: dataset  # dataset, capture-session, or template
schema_version: 1
```

## Minimum manifest fields

| Field | Meaning |
|---|---|
| `dataset_id` | Stable identifier used in docs and scripts. |
| `version` | Manifest/data revision. |
| `status` | `git-lfs`, `generated-local`, `manifest-only`, `local-only`, or `template`. |
| `title` | Human-readable dataset title. |
| `description` | What the recording contains and why it exists. |
| `file_name` | Expected local file name after download. |
| `storage` | `repo`, `git-lfs`, `external-url`, or `private`. |
| `url` | External URL when the file is not stored in the repository. |
| `sha256` | File checksum for reproducibility. |
| `format` | `ci16`, `cu8`, `cf32`, WAV IQ, or another explicit format. |
| `endianness` | Byte order for integer formats. |
| `sample_rate_hz` | IQ sample rate. |
| `center_frequency_hz` | RF center frequency or baseband reference. |
| `bandwidth_hz` | Approximate receiver bandwidth. |
| `duration_s` | Recording duration. |
| `source` | SDR board, receiver, generator, antenna, synthetic model, or unknown. |
| `hardware` | Receiver/transmitter and important settings. |
| `gain` | RX/TX gain values when available. |
| `license` | Dataset license or access limitation. |
| `analysis_targets` | Expected plots, metrics or labs using the dataset. |
| `quality_checks` | Machine-readable validation state and measured quality gates. |

## Example manifest

```yaml
manifest_kind: dataset
schema_version: 1
dataset_id: lab09_ci16_tone_demo_v1
version: 1.0
status: external-url
title: CI16 tone capture demo
description: Short educational IQ recording containing a single narrowband tone for spectrum and metadata validation.
storage: external-url
url: https://example.invalid/datasets/lab09_ci16_tone_demo_v1.ci16
file_name: lab09_ci16_tone_demo_v1.ci16
sha256: replace-with-real-sha256
format: ci16
endianness: little
sample_rate_hz: 2400000
center_frequency_hz: 100000000
bandwidth_hz: 1200000
duration_s: 2.0
source: rtl-sdr-observation
hardware:
  receiver: RTL-SDR V3 Pro
  transmitter: Zynq-7020 + AD9363
  rf_path: conducted path with attenuation or controlled low-power OTA
  attenuation_db: 40
  rx_gain_db: 20
license: course-demo-only
analysis_targets:
  - spectrum estimate
  - peak frequency detection
  - noise floor estimate
  - metadata parser test
quality_checks:
  checksum_verified: true
  clipping_checked: true
notes:
  - Use only after verifying the checksum.
  - Do not assume this recording is calibrated for absolute power measurements.
```

## Directory convention

Recommended layout for future datasets:

```text
datasets/
  README.md
  manifests/
    lab09_ci16_tone_demo_v1.yml
    lab11_qpsk_loopback_v1.yml
  small/
    synthetic_ci16_smoke_test.ci16
```

Large recordings should not be committed directly to Git. Use external storage or Git LFS, then reference them from manifest files.

## Analysis workflow

```text
manifest.yml -> download or locate file -> verify sha256 -> parse format -> run analysis -> save plots -> save report
```

Every analysis script should print the manifest ID, file format, sample rate and checksum result before computing metrics.

## Metadata quality checklist

A dataset is acceptable for course use when:

- the sample format is unambiguous;
- the sample rate and center frequency are known;
- a checksum is available;
- the RF path and gain settings are described;
- the license or access policy is clear;
- at least one script can read it;
- expected plots or metrics are defined.

## Common mistakes

| Mistake | Consequence |
|---|---|
| Missing sample rate | Frequency axis and spectra become meaningless. |
| Unknown IQ format | Data may be parsed with wrong scaling or byte order. |
| No checksum | Reproducibility is not guaranteed. |
| No gain settings | Measurements cannot be compared across captures. |
| Large binary committed to Git | Repository clone becomes slow and hard to maintain. |
| No license / access note | Dataset cannot be safely reused in teaching or publications. |
