# Lab 11.6 - Measurement uncertainty budget and reporting

## Goal

Standardize engineering reporting for measured metrics using:

- Type A and Type B uncertainty contributions;
- root-sum-square combined standard uncertainty;
- expanded uncertainty with coverage factor `k=2`.

## Engineering question

> How do we report a metric (for example EVM) with a defensible uncertainty interval instead of a single raw number?

## Executable file

| File | Purpose |
|---|---|
| `blocks/block_11_integrated_sdr_project/python/lab_11_6_measurement_uncertainty_budget.py` | uncertainty contribution example and report artifacts |

Run from the repository root:

```bash
python blocks/block_11_integrated_sdr_project/python/lab_11_6_measurement_uncertainty_budget.py
```

## Generated artifacts

```text
docs/assets/lab116_uncertainty_budget_contributions.png
docs/assets/lab116_uncertainty_budget_table.md
docs/assets/lab116_uncertainty_budget_metrics.json
```

## Core formulas

```text
u_c = sqrt(sum(u_i^2))
U = k * u_c, with k = 2 for approximately 95% coverage
reported result = nominal +/- U
```

## Report checklist

- [ ] Separate Type A and Type B sources.
- [ ] Show each standard contribution after distribution divisor.
- [ ] Provide `u_c`, `U(k=2)`, and final interval.
- [ ] State assumptions and limits of the uncertainty model.

