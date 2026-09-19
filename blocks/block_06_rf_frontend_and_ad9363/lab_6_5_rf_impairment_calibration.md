# Lab 6.5 - RF impairment calibration (DC, IQ imbalance, LO leakage)

## Goal

Build a reproducible calibration flow for common RF receiver impairments:

- DC offset;
- IQ gain/phase mismatch;
- LO leakage at baseband DC.

## Why this lab matters

An ideal zero-IF receiver would deliver a clean complex baseband. A real one adds
three artefacts that are easy to mistake for signal: a **DC offset** (a spike at 0 Hz
from ADC and mixer bias), **LO leakage** (the local oscillator itself leaking into the
signal path, which for a zero-IF receiver *also* lands at 0 Hz), and **I/Q imbalance**
(the two mixer arms are never exactly equal in gain or exactly 90 degrees apart),
which reflects every real signal to a mirror-image copy at the negative frequency. If
you do not recognise these, you will chase phantom tones, read a wrong SNR, and lose
several dB of constellation quality in every later lab. This lab makes each artefact
measurable so you can see it, remove it and know how much is left.

## Engineering question

> Can we quantify impairment metrics before/after calibration and show measurable improvement on spectrum and constellation?

## Executable file

| File | Purpose |
|---|---|
| `blocks/block_06_rf_frontend_and_ad9363/python/lab_6_5_rf_impairment_calibration.py` | impairment synthesis, calibration, metrics, plots |

Run from the repository root:

```bash
python blocks/block_06_rf_frontend_and_ad9363/python/lab_6_5_rf_impairment_calibration.py
```

## Generated artifacts

```text
docs/assets/lab65_rf_impairment_spectrum_before_after.png
docs/assets/lab65_rf_impairment_constellation_before_after.png
docs/assets/lab65_rf_impairment_calibration_metrics.json
```

## Metrics

| Metric | Meaning |
|---|---|
| `dc_offset_rms` | complex mean magnitude of IQ samples |
| `iq_gain_mismatch_db` | I vs Q RMS mismatch in dB |
| `iq_cross_correlation` | residual non-orthogonality between I and Q |
| `image_rejection_db` | desired tone power vs image tone power |
| `lo_leakage_dbfs` | LO/DC leakage level relative to peak tone |

## Calibration stages

1. Remove complex DC component.
2. Match I/Q RMS amplitudes.
3. Orthogonalize Q against I (Gram-Schmidt style).
4. Remove residual DC again.

## What to expect

With the default synthetic impairments (DC = 0.085 − j0.052, 1.7 dB I/Q gain mismatch,
6.5° phase skew, LO leakage 0.14 at −30°, noise rms 0.015, 180 kHz tone at 2.4 MS/s):

```text
DC offset RMS before/after: 0.239629 / 0.000000
Image rejection (dB) before/after: 19.16 / 78.77
IQ cross-correlation before/after: 0.1131 / 0.0000
```

and, from `lab65_rf_impairment_calibration_metrics.json`, LO leakage improves from
−10.2 dBFS to −86.1 dBFS and the I/Q gain mismatch from −1.64 dB to 0 dB.

How to read these numbers:

- **Image rejection of 19 dB is what those imbalances predict.** A first-order
  estimate is `IRR ≈ 10·log10(4 / (ε² + φ²))` with amplitude error `ε ≈ 0.22`
  (1.7 dB) and phase error `φ ≈ 0.11 rad` (6.5°), which gives about 18–19 dB. In
  practice this means a strong signal at +180 kHz also shows up at −180 kHz only
  ~19 dB lower — enough to fake an interferer.
- **DC offset and LO leakage collapse together** because in a zero-IF receiver both
  sit at exactly 0 Hz; removing the complex mean removes both.
- **The "after" numbers are unrealistically good** (78.8 dB image rejection,
  −86 dBFS leakage, DC at `1e-17`). That is because this compact method estimates
  each correction from the same noiseless-enough 65 536-sample synthetic record it
  then corrects, so the estimate is essentially exact. On real hardware the
  estimate is limited by noise, by temperature and gain drift, and by the fact that
  imbalance varies with frequency across the band. Expect a real calibration to
  reach tens of dB, not 78, and to have to be repeated.

## Exercises

1. Set `iq_gain_mismatch_db` to 0 and keep the 6.5° skew. How much of the image is
   left? Then do the opposite. Which impairment matters more for this tone?
2. Halve `noise_rms` and re-run. Does the "after" image rejection change? Why or
   why not?
3. Move the tone from 180 kHz to 5 kHz. What happens to the tone, the DC spike and
   the image, and what does that tell you about signals near 0 Hz in a zero-IF
   receiver?

## Report checklist

- [ ] Show before/after spectrum and constellation.
- [ ] Report all five metrics before and after calibration.
- [ ] Explain which metric improved the most and why.
- [ ] State limits of this compact calibration method for real hardware.

