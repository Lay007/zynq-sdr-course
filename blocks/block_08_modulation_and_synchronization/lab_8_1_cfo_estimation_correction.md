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

## What to expect

Default run (4096 QPSK symbols at 1 MS/s, one sample per symbol, CFO 2750 Hz, phase 0.65 rad,
noise 0.035 rms, seed 81):

```text
True CFO: 2750.000 Hz
Estimated CFO: 2750.039 Hz
CFO error: 0.039 Hz
EVM before: 141.442 % (3.01 dB)
EVM after: 4.985 % (-26.05 dB)
BER before: 5.002441e-01 (4098/8192)
BER after: 0.000000e+00 (0/8192)
Residual phase estimate: 0.650010 rad
```

- **BER 0.5 before correction** means the decisions are random: the constellation turns
  `360 * 2750 / 1e6 ≈ 1°` per symbol, so over 4096 symbols it spins more than 11 times.
- **The estimate is within 0.04 Hz**, because a straight-line fit over 4096 samples averages the
  noise very effectively at this SNR.
- **The residual phase 0.650 rad recovers the injected 0.65 rad.** After removing the CFO, one
  constant phase remains. The metrics are computed on the receiver's own output, without aligning
  it to the known reference first, so a wrong phase estimate would show up as bit errors.

!!! note "A sign detail that matters"
    For QPSK points at `(±1±j)/√2`, every symbol raised to the 4th power equals `−1`. The phase
    estimate is therefore `angle(−mean(r⁴))/4`. Without the minus sign the estimate is off by
    exactly π/4 and the "corrected" constellation lands on the I/Q axes. This lab had exactly
    that bug until September 2026; it was hidden because BER was then computed after a genie
    alignment to the reference. [Lab 11.30](/zynq-sdr-course/en/labs/lab-11-30-two-board-cfo-validation/)
    describes the same trap on hardware.

## Exercises

1. The 4th-power estimator is unambiguous for `|CFO| < Fs/8` = 125 kHz here. Set the CFO to 50,
   100, 110 and 120 kHz. At 100 kHz the estimate is already about 175 Hz low, and at 120 kHz it
   collapses to about 55 kHz. Why is the practical limit lower than 125 kHz? (Hint: `np.unwrap`
   needs every sample-to-sample step of `angle(r⁴)` to stay below π.)
2. Raise the noise from 0.035 to 0.2 and 0.35. The estimate error grows to hundreds, then
   thousands of hertz. Explain why a phase-unwrap-based estimator fails abruptly rather than
   degrading smoothly.
3. Replace the straight-line fit with the mean of `angle(r⁴[n+1] · conj(r⁴[n]))`. Compare the
   error at noise 0.2.
4. Remove the minus sign in `estimate_phase_qpsk` and rerun. Report EVM and BER after correction
   and explain them.

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
