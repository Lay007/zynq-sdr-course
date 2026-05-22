# Lab 3.5 — FFT complexity and selected-bin trade-off

This lab strengthens the DSP foundation of the course without using notebooks. It is a deterministic script-driven lab that connects transform complexity to SDR measurement and FPGA design decisions.

## Goal

Compare three analysis strategies:

| Strategy | When it is useful | Engineering consequence |
|---|---|---|
| Direct DFT | Small reference vectors and teaching. | Simple but scales poorly. |
| Full FFT | Spectrum displays, measurement dashboards and unknown signals. | Efficient full-spectrum analysis, but requires memory, ordering and architecture choices. |
| Selected-bin detection | Known tones, pilots or narrow checks. | Can be cheaper than full FFT when only a few frequencies matter. |

## Run command

From the repository root:

```bash
python blocks/block_03_dsp_basics/python/lab_3_5_fft_complexity.py
```

Or run it as part of the reproducibility suite:

```bash
python tools/run_all_labs.py
```

## Generated artifacts

| Artifact | Purpose |
|---|---|
| `docs/assets/lab35_dft_fft_complexity.png` | Direct DFT vs FFT operation growth. |
| `docs/assets/lab35_selected_bin_tradeoff.png` | Full-spectrum FFT vs selected-bin detector. |
| `docs/assets/lab35_fft_complexity_metrics.json` | Machine-readable ratios for CI and reports. |

## Engineering questions

1. At what vector sizes does direct DFT become unreasonable for SDR analysis?
2. When is a full FFT justified instead of selected-bin detection?
3. How would the choice change for an FPGA streaming design?
4. What memory and latency trade-offs appear when moving from a script to RTL?

## Report checklist

- Include both generated plots.
- Report the DFT/FFT complexity ratio at the largest tested `N`.
- Report the FFT/selected-bin ratio at the largest tested `N`.
- Explain which method you would use for:
  - spectrum monitoring;
  - single pilot detection;
  - wideband unknown-signal search;
  - FPGA resource-constrained implementation.

## Bridge to later blocks

This lab feeds directly into:

- Block 05: FFT resource and streaming architecture decisions;
- Block 08: pilot and synchronization detection;
- Block 09: spectrum analysis of recorded IQ files;
- Block 11: measurement dashboard design.
