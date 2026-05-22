# Lab 3.7 — Window trade-offs and weak-signal detection

This lab strengthens the spectral-analysis part of the DSP foundation track. It is a deterministic script-driven lab, not a notebook workflow.

## Goal

Show that FFT windows are engineering choices, not decorative plotting options. The lab compares how different windows affect the visibility of a weak tone located near a stronger tone.

## What is measured

| Window property | SDR measurement consequence |
|---|---|
| Main-lobe width | Tone separation and frequency resolution. |
| Side-lobe level | Ability to observe weak signals near strong components. |
| Coherent gain | Correct amplitude interpretation. |
| ENBW | Noise-floor interpretation and sensitivity. |

## Run command

From the repository root:

```bash
python blocks/block_03_dsp_basics/python/lab_3_7_window_tradeoffs.py
```

Or run it as part of the reproducibility suite:

```bash
python tools/run_all_labs.py
```

## Generated artifacts

| Artifact | Purpose |
|---|---|
| `docs/assets/lab37_window_tradeoffs.png` | Spectrum comparison for rectangular, Hann and Blackman windows. |
| `docs/assets/lab37_weak_signal_detection.png` | Weak-signal visibility metric by window. |
| `docs/assets/lab37_window_metrics.json` | Coherent gain, ENBW and weak-signal metrics. |

## Engineering questions

1. Why can a rectangular window hide a weak signal near a strong signal?
2. Why does lower side-lobe level usually come with a wider main lobe?
3. Why is coherent gain required for amplitude interpretation?
4. Why does ENBW matter for noise-floor measurements?
5. Which window would you choose for weak-signal detection and why?

## Report checklist

- Include both generated plots.
- Compare at least three window types.
- Report coherent gain and ENBW.
- Report the weak-tone visibility metric.
- Explain how window choice affects SDR spectrum displays and measurement reports.

## Bridge to later blocks

This lab feeds directly into:

- Block 06: RF spectrum observation and overload checks;
- Block 08: synchronization and weak-pilot detection;
- Block 09: analysis of recorded IQ files;
- Block 11: measurement dashboard and final report quality.
