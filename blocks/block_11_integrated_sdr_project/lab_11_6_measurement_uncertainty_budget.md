# Lab 11.6 - Measurement uncertainty budget and reporting

## Goal

Standardize engineering reporting for measured metrics using:

- Type A and Type B uncertainty contributions;
- root-sum-square combined standard uncertainty;
- expanded uncertainty with coverage factor `k=2`.

## Why this lab matters

A single EVM number such as "3.8 %" hides how much it could be off. The instrument has a stated
accuracy, the cable drifts, the reference clock is not perfect, and the temperature changed
while you measured. If you do not account for these, two engineers cannot tell whether
"3.8 %" and "4.1 %" are different or the same. An uncertainty budget makes every contribution
explicit and combines them by a standard rule, so the result is reported as a defensible
interval and you can see which contribution to attack first.

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

## What to expect

The example budget (nominal EVM 3.8 %) prints and stores:

| Source | Distribution | Input | Divisor | Standard contribution |
|---|---|---:|---:|---:|
| repeatability (Type A) | normal | 0.0222 | 1 | 0.0222 |
| instrument amplitude accuracy | rectangular | 0.2000 | 1.7321 | 0.1155 |
| reference clock tolerance | rectangular | 0.0800 | 1.7321 | 0.0462 |
| cable + connector drift | rectangular | 0.1200 | 1.7321 | 0.0693 |
| temperature effect | normal | 0.1000 | 1 | 0.1000 |

```text
Combined standard uncertainty: 0.1754% EVM
Expanded uncertainty (k=2): 0.3508% EVM
Report interval: [3.449, 4.151]%
```

How to read it:

- **A rectangular limit of half-width `a` becomes a standard uncertainty `a / sqrt(3)`**
  (that is the divisor column: 0.2 / 1.7321 = 0.1155); normal contributions are used as given.
- **The result is dominated by the instrument accuracy (0.1155) and temperature (0.1000)**, both
  Type B. The measured repeatability (Type A, 0.0222) is the smallest term, so repeating the
  measurement 100 more times would barely change the interval; a better instrument or a
  temperature-controlled setup would.
- **The answer is a statement, not a number:** `EVM = 3.800 % +/- 0.351 % (k = 2)`. Two results are
  only distinguishable if their intervals do not overlap.

## Report checklist

- [ ] Separate Type A and Type B sources.
- [ ] Show each standard contribution after distribution divisor.
- [ ] Provide `u_c`, `U(k=2)`, and final interval.
- [ ] State assumptions and limits of the uncertainty model.

