# Lab 8.2 — Phase Offset Estimation and Decision-Directed Correction

## Goal

Inject a constant phase offset into a QPSK signal, estimate it, correct it and compare constellation quality before and after correction.

The lab answers the practical question:

> After CFO has been corrected, how do we remove the remaining constant constellation rotation?

## Executable files

| Environment | File | Output |
|---|---|---|
| Python | `blocks/block_08_modulation_and_synchronization/python/lab_8_2_phase_offset_correction.py` | constellation plots, EVM comparison and metrics JSON in `docs/assets` |

Run from the repository root:

```bash
python blocks/block_08_modulation_and_synchronization/python/lab_8_2_phase_offset_correction.py
```

Generated artifacts:

```text
docs/assets/lab82_phase_constellation_before.png
docs/assets/lab82_phase_constellation_after_blind.png
docs/assets/lab82_phase_constellation_after_dd.png
docs/assets/lab82_phase_evm_comparison.png
docs/assets/lab82_phase_metrics.json
```

## Processing chain

```mermaid
flowchart LR
    BITS[Random bits] --> QPSK[QPSK symbols]
    QPSK --> PHASE[Apply phase offset]
    PHASE --> NOISE[Add noise]
    NOISE --> BLIND[4th-power phase estimate]
    BLIND --> DD[Decision-directed refinement]
    DD --> DEC[Hard decisions]
    DEC --> METRICS[EVM and BER]
```

## Phase model

After carrier frequency correction, a constant phase offset may remain:

```text
r[n] = s[n] * exp(j*phi0) + noise[n]
```

This rotates the entire constellation by `phi0`.

## Blind QPSK phase estimate

For QPSK, the 4th-power operation removes the symbol data approximately:

```text
phase_est = angle(mean(r[n]^4)) / 4
```

This estimator has a `pi/2` ambiguity. For a real receiver, ambiguity is resolved by differential coding, known preamble, pilots or frame synchronization.

## Decision-directed refinement

After a coarse phase correction, decisions are made to the nearest QPSK points. The residual phase is then estimated between the received symbols and sliced decisions:

```text
phase_dd = angle(sum(conj(decision[n]) * r[n]))
```

This is useful when the constellation is already close enough for mostly correct decisions.

## Metrics

| Metric | Meaning |
|---|---|
| true phase offset | intentionally injected rotation |
| blind phase estimate | 4th-power phase estimate |
| decision-directed phase estimate | refined total estimate |
| phase error | estimate minus true phase |
| EVM before | constellation error before correction |
| EVM after blind | error after 4th-power correction |
| EVM after decision-directed | error after refinement |
| BER before/after | decision quality before/after correction |

## Common mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| phase sign is wrong | constellation rotates further away | flip correction sign |
| `pi/2` ambiguity ignored | constellation maps to wrong bits | use preamble or differential coding |
| decision-directed starts too early | wrong decisions bias estimate | use coarse correction first |
| CFO still present | phase estimate drifts | correct CFO before phase offset |
| low SNR | phase estimate noisy | average more symbols or use pilots |

## What to expect

Default run (4096 QPSK symbols, phase offset 0.70 rad = 40°, noise 0.055 rms, seed 82):

```text
True phase offset: 0.700000 rad
Blind phase estimate: 0.699895 rad
Decision-directed total estimate: 0.700102 rad
Blind phase error: -0.000105 rad
Decision-directed phase error: 0.000102 rad
EVM before: 69.026 %
EVM after blind: 7.833 %
EVM after decision-directed: 7.833 %
BER before: 2.917480e-02 (239/8192)
BER after blind: 0.000000e+00 (0/8192)
BER after decision-directed: 0.000000e+00 (0/8192)
```

- **A 40° rotation already causes errors (BER 2.9 %)** because the points sit only 5° from the
  45° decision boundaries, and the noise pushes some of them across.
- **The blind 4th-power estimate is within 0.0001 rad**, and the decision-directed step has
  nothing left to fix; EVM after both is the noise floor (7.8 %).
- **The estimate is only unique inside ±π/4 (±45°).** 0.70 rad is inside that interval on
  purpose. See exercise 1 for what happens outside it.

!!! note "Corrected in September 2026"
    Until then this lab computed `angle(mean(r⁴))/4` without negating the mean (for these QPSK
    points `s⁴ = −1`), which put every estimate off by π/4, and it used 0.82 rad, which lies
    outside the unambiguous interval. The run reported BER 0.25 "after correction".

## Exercises

1. Set `phase_offset_rad` to 0.82 (47°). The blind estimate becomes 0.82 − π/2 = −0.75 rad, the
   corrected constellation is rotated by a quarter turn, and BER jumps to 0.5 although the
   constellation looks perfect. Why can the 4th-power estimator never tell 0.82 from −0.75, and
   how do a known preamble or differential coding fix it (see
   [Lab 8.7](/zynq-sdr-course/en/labs/lab-8-7-snr-vs-ber-traps/))?
2. Increase the noise until the decision-directed estimate becomes worse than the blind one.
   Why does a decision-directed estimator degrade faster at low SNR?
3. Estimate the phase from only the first 64, 256 and 1024 symbols. How does the estimate error
   scale with the number of symbols?

## Report checklist

- [ ] State modulation type and symbol count.
- [ ] State true phase offset.
- [ ] Explain 4th-power phase estimation.
- [ ] Explain `pi/2` ambiguity.
- [ ] Explain decision-directed refinement.
- [ ] Include constellation before correction.
- [ ] Include constellation after blind correction.
- [ ] Include constellation after decision-directed correction.
- [ ] Report EVM and BER before/after.

## Engineering conclusion template

```text
The QPSK signal used a phase offset of ____ rad. The blind estimator measured ____ rad,
and the decision-directed refinement measured ____ rad. EVM improved from ____ % to ____ %,
and BER changed from ____ to ____. The remaining limitation is ______.
```
