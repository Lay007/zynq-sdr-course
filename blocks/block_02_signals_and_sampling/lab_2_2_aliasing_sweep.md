# Lab 2.2 — Aliasing Sweep

## Goal

Show how real-valued sampling folds tones above Nyquist back into the observable band and why aliasing must be predicted before interpreting a spectrum.

## Why this matters

If a tone above `Fs/2` is sampled without adequate filtering, the observed spectrum contains an alias rather than the original RF tone. Without an aliasing model, a measured peak can be assigned to the wrong source.

## Experiment

The script uses:

- sample rate `Fs = 1.0 MHz`;
- a real-valued sampler model;
- example tones at `180 kHz`, `620 kHz` and `1.18 MHz`.

It produces:

- an aliasing map from `0` to `2.5 * Fs`;
- example spectra for the three test tones;
- measured vs expected alias frequencies.

## Run

From the repository root:

```bash
python blocks/block_02_signals_and_sampling/python/aliasing_sweep.py
```

Or run the representative lab pack:

```bash
python tools/run_all_labs.py
```

## Expected artifacts

| Artifact | Meaning |
|---|---|
| `docs/assets/lab22_aliasing_map.png` | mapping from input tone to observed alias magnitude |
| `docs/assets/lab22_aliasing_examples.png` | spectra for tones below and above Nyquist |
| `docs/assets/lab22_aliasing_metrics.json` | expected aliases, measured aliases and max alias error |

## Interpretation checks

- The `180 kHz` tone should appear close to its original frequency because it is below Nyquist.
- The `620 kHz` tone should fold to approximately `380 kHz`.
- The `1.18 MHz` tone should fold to approximately `180 kHz`.
- The metrics JSON should confirm that measured alias frequencies follow the analytical alias model within a small error.

## What to expect

```text
Input 180000 Hz -> expected alias 180000.000 Hz, measured 179992.676 Hz
Input 620000 Hz -> expected alias 380000.000 Hz, measured 380004.883 Hz
Input 1180000 Hz -> expected alias 180000.000 Hz, measured 179992.676 Hz
```

- For a **real** sampler at `Fs = 1 MHz` the observable band is 0 to 500 kHz. A tone at `f`
  appears at `|f - k*Fs|` for the integer `k` that lands in that band.
- **180 kHz and 1.18 MHz produce the same spectrum.** From the samples alone they cannot be told
  apart. Only an analog filter *before* the ADC can decide which one is allowed in.
- The few-hertz differences between expected and measured are bin quantization, as in Lab 2.1.

## Exercises

1. Predict the alias of 950 kHz, 1.5 MHz and 2.3 MHz at `Fs = 1 MHz`, then check.
2. Which input frequencies between 0 and 3 MHz all land exactly on 100 kHz?
3. A receiver has an anti-alias filter with a 450 kHz passband edge. Which band of inputs can
   still fold into 0–50 kHz if the filter only reaches 40 dB rejection at 950 kHz?

## Report checklist

- [ ] Record `Fs` and the Nyquist frequency.
- [ ] Explain why the lab uses a real-valued tone model.
- [ ] Attach the aliasing map and the example spectra.
- [ ] Compare measured aliases against analytical expectations.
- [ ] State what anti-alias filtering or sample-rate change would prevent the wrong interpretation.
