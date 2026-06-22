# Lab 9.5 — Synthetic QPSK replay and constellation analysis

## Goal

In this lab, the student follows a fully reproducible IQ-data workflow without the publication risks of real off-air content:

1. generate a synthetic QPSK dataset;
2. read CI16 IQ samples;
3. build constellation and spectrum previews;
4. produce JSON metrics;
5. connect the result to an engineering report.

This lab complements the real RTL-SDR/Zynq observations. Real captures prove the practical RF path, while the synthetic QPSK fixture provides a legally clean and deterministic signal for CI and teaching.

## Input artifacts

| Artifact | Purpose |
|---|---|
| `datasets/demo_qpsk_capture/manifest.yaml` | dataset and signal-parameter description |
| `datasets/demo_qpsk_capture/metrics.json` | generator metrics snapshot |
| `tools/generate_demo_qpsk_dataset.py` | deterministic CI16 QPSK generator |
| `tools/analyze_demo_qpsk_dataset.py` | dataset analyzer and preview asset generator |
| `reports/demo_qpsk_dataset_analysis.md` | reviewer-facing report example |

## Reproduction commands

Run from the repository root:

```bash
python tools/generate_demo_qpsk_dataset.py
python tools/analyze_demo_qpsk_dataset.py
```

If the CI16 file is missing, let the analyzer generate it automatically:

```bash
python tools/analyze_demo_qpsk_dataset.py --generate-if-missing
```

## Expected output files

| File | What to check |
|---|---|
| `datasets/demo_qpsk_capture/demo_qpsk_capture.ci16` | locally generated IQ payload, not committed |
| `datasets/demo_qpsk_capture/analysis_summary.json` | sample count, EVM, CFO and bandwidth metrics |
| `docs/assets/demo_qpsk_constellation.svg` | four compact QPSK clusters |
| `docs/assets/demo_qpsk_spectrum.svg` | synthetic QPSK spectrum preview |

## Acceptance metrics

Minimal acceptance criteria:

| Metric | Expected value |
|---|---:|
| `num_samples` | `16384` |
| `num_symbols` | `2048` |
| `sample_rate_hz` | `2400000` |
| `evm_rms_percent` | `< 0.01` |
| `abs(cfo_estimate_hz)` | `< 1.0` |

## Engineering interpretation

If the metrics pass the thresholds, then:

- the CI16 format is read correctly;
- the I/Q order is not swapped;
- symbol sampling is consistent with `samples_per_symbol`;
- the constellation has the expected QPSK structure;
- the analyzer can be used as a baseline smoke test for future real-capture analyzers.

## What to include in the lab report

The lab report should include:

1. reproduction commands;
2. a short excerpt from `analysis_summary.json`;
3. constellation preview;
4. spectrum preview;
5. a short explanation of why a synthetic dataset is useful next to real RF captures.

## CI connection

This lab is covered by:

```text
.github/workflows/qpsk_demo_analysis.yml
```

The CI workflow checks that the dataset is generated, the analyzer runs, output files are created and key metrics stay within thresholds.

## Next step

After this lab, the course can compare the synthetic QPSK fixture with real IQ recordings and add impairment models: CFO, DC offset, IQ imbalance, AWGN and timing offset.
