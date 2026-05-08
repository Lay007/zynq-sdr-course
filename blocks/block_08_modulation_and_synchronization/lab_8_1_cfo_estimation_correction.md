# Lab 8.1 — Carrier Frequency Offset Estimation and Correction

## Goal

Inject carrier frequency offset into a QPSK signal, estimate it, compensate it and evaluate constellation quality before and after synchronization.

The lab answers the practical question:

> Why does the constellation rotate, and how can we estimate and remove this rotation before symbol decisions?

## Executable files

| Environment | File | Output |
|---|---|---|
| Python | `blocks/block_08_modulation_and_synchronization/python/lab_8_1_cfo_estimation_correction.py` | constellation plots, phase plot and metrics JSON in `docs/assets` |

Run from the repository root:

```bash
python blocks/block_08_modulation_and_synchronization/python/lab_8_1_cfo_estimation_correction.py
```

Generated artifacts:

```text
docs/assets/lab81_cfo_constellation_before.png
docs/assets/lab81_cfo_constellation_after.png
docs/assets/lab81_cfo_phase_evolution.png
docs/assets/lab81_cfo_metrics.json
```

## Processing chain

```mermaid
flowchart LR
    BITS[Random bits] --> QPSK[QPSK symbols]
    QPSK --> CFO[Apply CFO + phase offset]
    CFO --> NOISE[Add noise]
    NOISE --> EST[Estimate CFO]
    EST --> CORR[Correct CFO]
    CORR --> PHASE[Correct residual phase]
    PHASE --> DEC[Hard decisions]
    DEC --> METRICS[EVM and BER]
```

## CFO model

Carrier frequency offset rotates each symbol by a linearly increasing phase:

```text
r[n] = s[n] * exp(j * (2*pi*f_cfo*n/Fs + phi0)) + noise[n]
```

If `f_cfo` is nonzero, the constellation does not stay fixed. It rotates over time.

## 4th-power method for QPSK

For QPSK, raising the signal to the 4th power removes the data modulation approximately:

```text
r4[n] = r[n]^4
```

The phase slope of `r4[n]` is four times the CFO phase slope. Therefore:

```text
f_cfo_est = slope(angle(r[n]^4)) * Fs / (2*pi*4)
```

This is a compact educational estimator. In real systems, preamble-based estimators and tracking loops are often more robust.

## Metrics

| Metric | Meaning |
|---|---|
| true CFO | intentionally injected frequency offset |
| estimated CFO | 4th-power estimator result |
| CFO error | estimated minus true CFO |
| EVM before | constellation error before synchronization |
| EVM after | constellation error after CFO/phase correction |
| BER before | hard-decision BER before correction |
| BER after | hard-decision BER after correction |
| residual phase | estimated constant phase after CFO correction |

## Expected plots

- constellation before CFO correction;
- constellation after CFO correction;
- unwrapped phase evolution before/after correction.

## Common mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| CFO sign is wrong | rotation becomes faster | flip correction sign |
| phase not corrected | constellation remains rotated | estimate residual phase |
| estimator used on low SNR | CFO estimate noisy | use longer averaging or preamble |
| wrong sample rate | CFO estimate scaled incorrectly | check metadata |
| using real-only signal | QPSK symmetry is broken | use complex IQ |

## Report checklist

- [ ] State modulation type and symbol count.
- [ ] State true CFO and sample rate.
- [ ] Explain the 4th-power estimator.
- [ ] Report estimated CFO and CFO error.
- [ ] Include constellation before correction.
- [ ] Include constellation after correction.
- [ ] Include phase evolution plot.
- [ ] Report EVM and BER before/after.
- [ ] Explain residual limitations.

## Engineering conclusion template

```text
The QPSK signal used a true CFO of ____ Hz. The 4th-power estimator measured ____ Hz,
giving an error of ____ Hz. After correction, EVM improved from ____ % to ____ % and
BER changed from ____ to ____. The result confirms / does not confirm that CFO was the
main synchronization impairment because ______.
```
