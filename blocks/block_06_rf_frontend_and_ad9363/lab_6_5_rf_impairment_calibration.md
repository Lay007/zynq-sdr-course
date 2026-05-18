# Lab 6.5 - RF impairment calibration (DC, IQ imbalance, LO leakage)

## Goal

Build a reproducible calibration flow for common RF receiver impairments:

- DC offset;
- IQ gain/phase mismatch;
- LO leakage at baseband DC.

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

## Report checklist

- [ ] Show before/after spectrum and constellation.
- [ ] Report all five metrics before and after calibration.
- [ ] Explain which metric improved the most and why.
- [ ] State limits of this compact calibration method for real hardware.

