# Measurement Uncertainty Guide

This page defines a compact reporting standard for SDR measurements used in this course.

## Why this is needed

A single measured value (for example EVM, SNR, or frequency error) is not sufficient for engineering decisions.
Each report should include an uncertainty interval and source breakdown.

## Required reporting structure

1. Nominal measured value.
2. Type A contribution (repeatability from repeated runs).
3. Type B contributions (instrument, clock, cabling, environment, model assumptions).
4. Combined standard uncertainty `u_c`.
5. Expanded uncertainty `U = k * u_c` with stated coverage factor `k`.
6. Final reported result:

```text
metric = nominal +/- U (k=2)
```

## Example workflow

- Use the executable example in Lab 11.6:
  `blocks/block_11_integrated_sdr_project/python/lab_11_6_measurement_uncertainty_budget.py`
- Fill the reusable template:
  `templates/measurement_uncertainty_budget.template.md`

## Minimum checklist for each measurement report

- [ ] Metric definition and units are explicit.
- [ ] Repeatability dataset is attached (or summarized).
- [ ] Type B sources are listed with distributions/divisors.
- [ ] Combined and expanded uncertainty are computed.
- [ ] Final interval is interpreted in engineering terms.
- [ ] Residual risks and assumptions are documented.

