# Demo QPSK Capture Dataset

This folder defines a small deterministic synthetic QPSK dataset for replay, constellation analysis and CI-safe IQ-processing checks.

The raw `demo_qpsk_capture.ci16` file is intentionally not committed. It is generated locally from a deterministic seed so the dataset remains reproducible without adding binary payload to the repository.

## Generate the dataset

Run from the repository root:

```bash
python tools/generate_demo_qpsk_dataset.py
```

This writes:

| File | Purpose |
|---|---|
| `demo_qpsk_capture.ci16` | Generated interleaved CI16 IQ samples, I first, little-endian |
| `manifest.yaml` | Dataset contract, checksum and signal parameters |
| `metrics.json` | Deterministic metrics snapshot |

## Analyze the dataset

Generate the analysis summary and report-ready SVG assets:

```bash
python tools/analyze_demo_qpsk_dataset.py --generate-if-missing
```

This produces:

| File | Purpose |
|---|---|
| `analysis_summary.json` | Analysis metrics for the synthetic QPSK fixture |
| `docs/assets/demo_qpsk_constellation.svg` | Constellation preview |
| `docs/assets/demo_qpsk_spectrum.svg` | Spectrum preview |

## Validate metadata

```bash
python tools/check_dataset_manifests.py
```

The checker validates the manifest fields and verifies that `metrics.json` agrees with the manifest SHA256. If the raw CI16 file is present locally, the checker also verifies its checksum.

## Signal parameters

| Parameter | Value |
|---|---:|
| Modulation | QPSK |
| Sample rate | 2.4 MS/s |
| Symbol rate | 300 ksym/s |
| Samples per symbol | 8 |
| Symbols | 2048 |
| Samples | 16384 |
| CI16 payload size | 65536 bytes |

## Why this dataset exists

The real RTL-SDR captures in `datasets/lab1_0_rtl_sdr_observation/` prove that the course starts from real RF observations. This synthetic QPSK dataset serves a different role: it gives a legally clean, deterministic and CI-friendly IQ fixture for replay and analysis labs.

## Report reference

See `reports/demo_qpsk_dataset_analysis.md` for the report-style explanation of the generated analysis assets.
