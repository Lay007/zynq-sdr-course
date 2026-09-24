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

## What to expect

```text
rectangular: weak visibility = 0.45 dB
hann: weak visibility = 46.62 dB
blackman: weak visibility = 46.50 dB
```

- A weak tone 54 dB below a strong one, 8.4 kHz away (about 138 bins at 61 Hz per bin), is
  **invisible with a rectangular window** (0.45 dB above its local floor) and clearly visible with
  Hann or Blackman (about 46.5 dB).
- Here Hann and Blackman tie because the weak tone is far from the strong one, where both have
  leakage far below the noise. Compare Lab 3.1, where the weak tone is only 12 bins away and
  Blackman wins by 7.7 dB: which window is "best" depends on the spacing you need to resolve.

## Exercises

1. Move the weak tone closer to the strong one (for example 1.2 kHz, about 20 bins). Which window
   wins now?
2. Lower the weak tone to −80 dB. Which limit do you hit first: leakage or the noise floor?
3. Using the ENBW values from Lab 3.1, predict how much the noise floor rises from rectangular to
   Blackman, and check it on the plot.

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
