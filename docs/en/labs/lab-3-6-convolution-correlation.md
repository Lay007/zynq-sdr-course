# Lab 3.6 — Convolution and correlation for SDR

This lab separates two operations that are often confused in early DSP learning: convolution for filtering and correlation for detection. It is a deterministic script-driven lab, not a notebook workflow.

## Goal

Use one synthetic SDR-style signal to show two different engineering roles:

| Operation | SDR role | FPGA / implementation consequence |
|---|---|---|
| Convolution | FIR filtering, pulse shaping, channel response. | Multiply-accumulate structure, latency, coefficient quantization. |
| Correlation | Preamble detection, delay estimation, synchronization. | Sliding matched filter, accumulator width, threshold logic. |

## Run command

From the repository root:

```bash
python blocks/block_03_dsp_basics/python/lab_3_6_convolution_correlation.py
```

Or run it as part of the reproducibility suite:

```bash
python tools/run_all_labs.py
```

## Generated artifacts

| Artifact | Purpose |
|---|---|
| `docs/assets/lab36_convolution_filtering.png` | Shows convolution as FIR filtering. |
| `docs/assets/lab36_correlation_detection.png` | Shows matched correlation peak for preamble detection. |
| `docs/assets/lab36_correlation_metrics.json` | Delay estimate, delay error and peak-to-median metric. |

## Engineering questions

1. Why is convolution the natural operation for FIR filtering?
2. Why is correlation the natural operation for preamble detection?
3. How does noise affect the correlation peak?
4. What accumulator width would be required in a fixed-point correlator?
5. How would you implement a sliding correlator in FPGA logic?

## Report checklist

- Include both generated plots.
- Report the true and estimated delay.
- Report the delay error in samples.
- Report the correlation peak-to-median value.
- Explain how the FIR stage and matched correlator would map to RTL.

## Bridge to later blocks

This lab feeds directly into:

- Block 05: FIR and matched-filter RTL structures;
- Block 08: synchronization and preamble detection;
- Block 11: receiver-chain measurement reports.
