# Demo QPSK Dataset Analysis

## Goal

This report documents the deterministic synthetic QPSK dataset used for replay, constellation analysis and CI-safe IQ processing checks.

The dataset is synthetic. It contains no off-air content and can be regenerated from a deterministic seed.

## Input dataset

| Item | Value |
|---|---|
| Dataset | `datasets/demo_qpsk_capture/` |
| Raw IQ file | `demo_qpsk_capture.ci16` |
| Manifest | `manifest.yaml` |
| Base metrics | `metrics.json` |
| Analysis summary | `analysis_summary.json` |

## Reproduction commands

Generate the deterministic dataset:

```bash
python tools/generate_demo_qpsk_dataset.py
```

Run the analysis:

```bash
python tools/analyze_demo_qpsk_dataset.py
```

If the CI16 file is missing, allow the analyzer to generate it:

```bash
python tools/analyze_demo_qpsk_dataset.py --generate-if-missing
```

## Generated assets

| Asset | Purpose |
|---|---|
| `docs/assets/demo_qpsk_constellation.svg` | Visual constellation check |
| `docs/assets/demo_qpsk_spectrum.svg` | Spectrum preview |
| `datasets/demo_qpsk_capture/analysis_summary.json` | Machine-readable analysis metrics |

## Expected engineering result

The synthetic dataset should show:

- four compact QPSK constellation clusters;
- near-zero CFO estimate;
- very low EVM because the signal is deterministic and noise-free apart from CI16 quantization;
- a clean spectrum suitable for replay and tutorial analysis.

## Why this matters

The repository now has two complementary data classes:

1. **Real RTL-SDR off-air captures**  
   Useful for real-world observation and metadata discipline.

2. **Synthetic deterministic QPSK fixture**  
   Useful for CI-safe, legally clean and fully reproducible analysis.

This improves Block 9 and gives a stable IQ source for future EVM, CFO and synchronization examples.

## Suggested acceptance criteria

A review can treat the dataset analysis as healthy when:

- `analysis_summary.json` is regenerated without errors;
- constellation and spectrum SVG files are generated;
- RMS EVM remains below 0.01 percent;
- estimated CFO remains close to zero;
- sample count, symbol count and sample rate match the manifest.
