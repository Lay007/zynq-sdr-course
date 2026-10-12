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
2. Apply the decision-directed estimator on its own, without the blind step, to an offset of
   0.3 rad and then 0.6 rad, and raise the noise from 0.055 to 0.5. Compare its bias with the
   blind estimate. Why does a decision-directed estimator fail when the residual offset and the
   noise are both large?
3. Estimate the phase from only the first 64, 256 and 1024 symbols. How does the estimate error
   scale with the number of symbols?

<details markdown="1">
<summary>Answers (checked by running the lab script)</summary>

1. A 4th power maps every rotation by π/2 to the same value (`e^(j4(φ+π/2)) = e^(j4φ)`), so 0.82 and 0.82 − π/2 = −0.75 rad produce identical `r⁴`. The estimator only sees the constellation, and QPSK looks the same after a quarter turn. A known preamble tells which quadrant is which; differential coding puts the information in phase *changes*, which a constant rotation does not alter.
2. On its own, the decision-directed estimate is pulled towards zero. With a 0.3 rad offset its bias is −0.012 rad at noise 0.2, −0.075 at 0.3 and −0.20 rad at 0.5, while the blind estimate stays within 0.002 rad; at 0.6 rad the bias is already −0.24 rad at noise 0.2. A symbol pushed across a boundary by noise is decided as the neighbouring point, which lies *closer* to the rotated observation, so wrong decisions agree with the error instead of revealing it. Run after the blind step, as in this lab, the residual is near zero and the decision-directed step never loses: its rms error stays at or below the blind one down to Es/N0 ≈ 0 dB.
3. Over 200 noise seeds the rms error is 0.0069, 0.0036, 0.0017 and 0.0009 rad for 64, 256, 1024 and 4096 symbols: it halves for every four-fold increase, i.e. it falls as `1/√N`.

</details>

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
