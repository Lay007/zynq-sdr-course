# AGC/LNA Gain-Transition Phase-Discontinuity Report

Use this template for hardware issue #58. Do not fill it with guessed or simulated values. Every promoted row or figure must come from a real board session; a synthetic self-test run of `lab_6_10_agc_phase_transition_analysis.py` proves the analysis method only and must be labeled `[SYNTHETIC]` if referenced here at all.

## 1. Session metadata

| Field | Value |
|---|---|
| Date | TBD |
| Operator | TBD |
| Board | Zynq-7020 + AD936x-compatible SDR |
| RF frontend | AD9361 / AD9363 |
| Gain control mode | manual / slow_attack / fast_attack / hybrid |
| Reference receiver | AD9361/AD9363 capture via IIO |
| RF path | cabled / attenuated |
| Center frequency | TBD |
| Sample rate | TBD |
| Capture format | TBD |

## 2. Safety pre-check

- [ ] TX/input power path is understood and conservative.
- [ ] External attenuation is inserted for the cabled baseline.
- [ ] Fixed-gain baseline reproduced first, before enabling AGC.
- [ ] Local regulations and lab RF rules are respected.

## 3. Fixed-gain baseline (step 1)

| Field | Value |
|---|---|
| RX gain, dB | TBD |
| RSSI / dBFS | TBD |
| CFO, Hz | TBD |
| EVM, % | TBD |
| BER | TBD |
| Reference IQ capture | path/filename |

## 4. AGC configuration (step 2)

| Field | Value |
|---|---|
| Gain-control mode selected | TBD |
| Relevant AD9361/AD9363 register(s) / iio_attr | TBD |
| Input-level control method | digital attenuator / fixed pad swap / TX level step |
| Gain-table regions exercised | TBD |

## 5. Transition capture (step 3)

One row per captured transition. `sample_index`, amplitude step and phase discontinuity come directly from `lab_6_10_agc_phase_transition_analysis.py`'s JSON output; do not hand-estimate them from a plot.

| Transition ID | Capture file | sample_index | Gain before -> after | Amplitude step, dB | Phase discontinuity, deg | Recovery, samples | Notes |
|---|---|---:|---|---:|---:|---:|---|
| AGC-001 | | | | | | | |

## 6. Required plots

- [ ] gain-state / input-level versus time;
- [ ] amplitude (dBFS) versus time around the transition;
- [ ] phase error versus time around the transition, with the fitted pre-transition CFO trend overlaid;
- [ ] constellation before / during / after the transition (only if a known modulation is present);
- [ ] EVM versus time, if a known reference modulation is present.

## 7. Evaluation

Answer explicitly, from the measured `phase_discontinuity_rad`/`_deg` and `recovery_samples` fields, not from visual impression:

1. Is the phase discontinuity at the transition larger than the CFO-driven trend alone would predict? By how much?
2. Is the discontinuity repeatable across transitions of the same gain-table region, or does it vary?
3. How many samples does carrier tracking need to recover after the transition (if a carrier-recovery loop is in the loop)?
4. What BER/PER/EVM impact, if any, is attributable to the transition rather than to steady-state noise?
5. Is the observed behavior deterministic, state-dependent (specific gain-table boundary) or variable across repeats?

## 8. Comparison against the fixed-gain baseline

| Metric | Fixed gain (Section 3) | AGC, around transition | Delta |
|---|---:|---:|---:|
| EVM, % | | | |
| BER | | | |
| Frame-sync loss observed | | | |

## 9. Conclusion

```text
TBD: state whether the measured phase discontinuity is significant relative to
the existing carrier-recovery loop's tracking range, whether it is deterministic
or state-dependent, and whether a specific mitigation (loop reset, detector,
gain-table hysteresis) is justified by this measurement rather than assumed.
```

## Reproducibility

```bash
python blocks/block_06_rf_frontend_and_ad9363/python/lab_6_10_agc_phase_transition_analysis.py \
  <capture> --metadata <capture>.json --output <report>.json
```
