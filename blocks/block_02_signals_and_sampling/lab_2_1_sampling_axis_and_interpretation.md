# Lab 2.1 — Sampling Axis and Interpretation

## Goal

Verify that the same captured signal can produce a correct-looking but incorrect engineering conclusion if the sampling rate is interpreted incorrectly.

## Why this matters

A spectrum plot is only meaningful together with the correct `Fs`. If `Fs` is wrong, every FFT bin is mapped to the wrong physical frequency, even when the plot shape itself still looks plausible.

## Experiment

The script generates a complex tone with:

- correct sample rate `Fs = 1.0 MHz`;
- intentionally wrong interpretation `Fs = 0.8 MHz`;
- non-zero DC offset;
- additive noise;
- a known expected tone near `123.456 kHz`.

The lab compares:

- time-domain I/Q preview;
- FFT magnitude with the correct frequency axis;
- the same FFT magnitude with a wrong frequency axis;
- measured peak frequency error for both interpretations.

## Run

From the repository root:

```bash
python blocks/block_02_signals_and_sampling/python/sampling_analysis.py
```

Or run the representative lab pack:

```bash
python tools/run_all_labs.py
```

## Expected artifacts

| Artifact | Meaning |
|---|---|
| `docs/assets/lab21_sampling_time_domain.png` | I/Q preview in time domain |
| `docs/assets/lab21_sampling_frequency_axis.png` | correct vs wrong `Fs` interpretation on the FFT axis |
| `docs/assets/lab21_sampling_metrics.json` | expected tone, measured peaks and interpretation errors |

## Interpretation checks

- The correct interpretation should place the tone close to the expected `123.456 kHz`.
- The wrong interpretation should shift the measured peak significantly, even though the spectral shape still looks reasonable.
- The metrics JSON should show a small error for the correct axis and a much larger error for the wrong axis.
- The time-domain preview should also help detect DC offset and clipping risk before moving to frequency-domain conclusions.

## What to expect

```text
Expected tone: 123456.000 Hz
Measured peak with correct Fs: 123474.121 Hz
Measured peak with wrong Fs: 98779.297 Hz
Correct interpretation error: 18.121 Hz
Wrong interpretation error: -24676.703 Hz
```

- **The 18 Hz "error" with the correct Fs is not an error.** It is the FFT's bin quantization:
  the peak is read at the nearest bin centre. With 16 384 samples at 1 MS/s the bins are 61 Hz apart, so the error stays below half a bin.
- **With the wrong Fs every frequency is scaled by 0.8**: 123 474 x 0.8 = 98 779 Hz. The
  spectrum *shape* is identical, which is exactly why the mistake is easy to miss.
- A 20 % sample-rate mistake produced a 24.7 kHz frequency error. The metadata field `Fs` is
  therefore as important as the samples themselves.

## Exercises

1. The same file is read with Fs = 1.2 MHz by mistake. Predict the reported tone frequency
   before running.
2. How many samples do you need so that the bin quantization error is below 1 Hz at 1 MS/s?
3. A tone is known to be at 200.0 kHz, and your analysis reports 160.0 kHz. What sample rate
   did the analysis assume if the true rate is 1 MS/s?

## Report checklist

- [ ] Record the assumed `Fs`, FFT size and tone frequency.
- [ ] Explain why the same FFT magnitude can support both a correct and a wrong conclusion.
- [ ] Attach the time-domain preview and the frequency-axis comparison plot.
- [ ] Quote the correct and wrong frequency errors from the metrics JSON.
- [ ] State which metadata field must be protected in a real IQ capture workflow.
