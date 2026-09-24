# Lab 9.5 — Synthetic QPSK replay and constellation analysis

## Goal

In this lab, the student follows a fully reproducible IQ-data workflow without the publication risks of real off-air content:

1. replay the published synthetic QPSK dataset or regenerate it byte-for-byte;
2. read CI16 IQ samples;
3. build constellation and spectrum previews;
4. produce JSON metrics;
5. connect the result to an engineering report.

This lab complements the real RTL-SDR/Zynq observations. Real captures prove the practical RF path, while the synthetic QPSK fixture provides a legally clean and deterministic signal for CI and teaching.

## Input artifacts

| Artifact | Purpose |
|---|---|
| `datasets/demo_qpsk_capture/manifest.yaml` | dataset and signal-parameter description |
| `datasets/demo_qpsk_capture/demo_qpsk_capture.ci16` | public 64 KiB Git LFS replay payload |
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
| `datasets/demo_qpsk_capture/demo_qpsk_capture.ci16` | published IQ payload; SHA256 must match the manifest |
| `datasets/demo_qpsk_capture/analysis_summary.json` | checksum, BER/SER, sample count, EVM, CFO and bandwidth metrics |
| `docs/assets/demo_qpsk_constellation.svg` | four compact QPSK clusters |
| `docs/assets/demo_qpsk_spectrum.svg` | synthetic QPSK spectrum preview |

## Acceptance metrics

Minimal acceptance criteria:

| Metric | Expected value |
|---|---:|
| `num_samples` | `16384` |
| `num_symbols` | `2048` |
| `compared_bits` | `4096` |
| `bit_errors` / `symbol_errors` | `0` / `0` |
| `ber` / `ser` | `0.0` / `0.0` |
| `sample_rate_hz` | `2400000` |
| `evm_rms_percent` | `< 0.01` |
| `abs(cfo_estimate_hz)` | `< 1.0` |

## Engineering interpretation

If the metrics pass the thresholds, then:

- the CI16 format is read correctly;
- the I/Q order is not swapped;
- symbol sampling is consistent with `samples_per_symbol`;
- the recovered known payload has zero bit and symbol errors;
- the constellation has the expected QPSK structure;
- the analyzer can be used as a baseline smoke test for future real-capture analyzers.

## Impairment bridge to later labs

The ideal synthetic QPSK fixture is useful as a reference. The next learning step is to intentionally add impairments and observe how they appear in the same metrics and plots.

| Impairment | What happens to the signal | What to inspect in the analysis | Related block |
|---|---|---|---|
| CFO | the constellation rotates from symbol to symbol | increasing `cfo_estimate_hz`, smeared clusters | Block 8.1 CFO estimation/correction |
| Phase offset | all QPSK points rotate by a constant angle | rotated constellation while clusters stay compact | Block 8.2 Phase offset correction |
| Timing offset | samples are taken away from the symbol center | increasing EVM, degraded clusters, eye/symbol error | Block 8.3 Timing recovery |
| AWGN | points spread around the ideal constellation locations | increasing `evm_rms_percent`, lower SNR estimate | Block 7.3 / Block 8 sync metrics |
| DC offset | the constellation shifts away from zero | non-zero `mean_i_normalized` and `mean_q_normalized` | Block 6.5 RF impairment calibration |
| IQ imbalance | the constellation is stretched/skewed and image energy appears | asymmetric clusters and image component in the spectrum | Block 6.5 / Zero-IF artifacts |

Minimal experiment sequence:

1. keep the ideal-QPSK `analysis_summary.json` as the baseline;
2. add one impairment at a time;
3. rerun the analyzer;
4. compare EVM, CFO, mean I/Q, spectrum and constellation;
5. document which metric exposed the problem first.

This connects Block 9 to the synchronization and RF-calibration parts of the course. The same dataset first acts as a clean reference and then becomes a controlled test signal for compensation algorithms.

## Exercises

The analyzer on the committed dataset reports `evm_rms_percent = 0.00332`, `evm_peak_percent = 0.00332`, `snr_estimate_db = 89.59`, `mean_i_normalized = 0.0214` and a CFO estimate of the order of 1e-14 Hz.

1. Derive the EVM from the CI16 amplitude. Each QPSK component is 12000 / sqrt(2) = 8485.28, stored as 8485. Show that the rounding error gives exactly 0.00332 % and that 20 log10(1 / 3.32e-5) is the 89.6 dB SNR estimate.
2. Why is the peak EVM equal to the RMS EVM? (All four constellation points round the same way.) What would you expect on a real capture?
3. `mean_i_normalized` is 0.0214, not 0. Is that a DC offset? Count the +I and -I symbols in the payload and explain the value; then describe how you would tell data imbalance from a real receiver DC offset.
4. The CFO estimate is at the floating-point noise level and changes between runs in the last digits. Why must a real-capture analyzer report it with a stated resolution instead of printing it raw?

## What to include in the lab report

The lab report should include:

1. reproduction commands;
2. a short excerpt from `analysis_summary.json`;
3. constellation preview;
4. spectrum preview;
5. a short explanation of why a synthetic dataset is useful next to real RF captures;
6. a baseline-vs-one-impairment table when doing the extended task.

## CI connection

This lab is covered by:

```text
.github/workflows/qpsk_demo_analysis.yml
```

The CI workflow fetches the Git LFS payload, verifies its manifest and SHA256, replays it, checks zero BER/SER and regenerates it to confirm deterministic provenance.

## Next step

After this lab, add a controlled-impairment script for CFO, DC offset, IQ imbalance, AWGN and timing offset. This turns the ideal QPSK fixture into a test bench for synchronization and RF-calibration checks.
