# Lab 6.10 — AGC/LNA Gain-Transition Phase-Discontinuity Analysis

## Goal

The existing two-board QPSK link (Block 11) deliberately uses **fixed RX gain**. This lab turns on AD9361/AD9363 AGC on purpose and measures what a gain-state transition does to carrier phase, separated honestly from the ordinary phase rotation CFO already produces every sample.

> A receiver's phase keeps turning continuously because of CFO even with no gain event at all. A raw "phase before vs phase after" comparison at a gain step cannot tell a gain-correlated phase glitch apart from that ordinary rotation — the two must be separated by fitting the CFO trend and looking at the *residual* at the transition.

This complements [Lab 6.2](/zynq-sdr-course/en/labs/lab-6-2-gain-staging-and-overload/) and issue #29 (AD9363 gain table and overload limits), which characterize **static** gain/overload behavior. This lab is about **dynamic** gain transitions.

## Method

```text
fixed-gain baseline
    -> enable AGC
    -> force/observe a gain-state transition
    -> fit the pre-transition CFO trend (phase vs sample index)
    -> extrapolate the trend across the transition
    -> discontinuity = observed phase - extrapolated phase
    -> amplitude step, recovery time, EVM/BER impact
```

## Executable analysis tool

```text
blocks/block_06_rf_frontend_and_ad9363/python/lab_6_10_agc_phase_transition_analysis.py
```

Run the no-hardware self-test first:

```bash
python blocks/block_06_rf_frontend_and_ad9363/python/lab_6_10_agc_phase_transition_analysis.py --self-test
```

The self-test builds two synthetic captures sharing the same injected CFO and the same amplitude step: one with an additional injected phase discontinuity at the transition, one without (a control). A PASS means the tool recovers the injected discontinuity to within 0.05 rad on the first capture *and* reports near-zero on the control — i.e. it does not mistake ordinary CFO rotation for a gain-transition event. It proves the **analysis method**, not any real AD9361/AD9363 behavior.

For a real capture:

```bash
python blocks/block_06_rf_frontend_and_ad9363/python/lab_6_10_agc_phase_transition_analysis.py \
  measurements/agc_001.ci16 --metadata measurements/agc_001.json \
  --output measurements/agc_001_analysis.json
```

The metadata sidecar follows `templates/gain_transition_capture_metadata.template.json`: sampling format/rate and a `gain_transitions` list of `sample_index` values (plus the gain-control mode and settings for the report). Every listed transition is analyzed independently.

## Procedure

1. **Baseline with fixed RX gain.** Reproduce the existing two-board cabled QPSK link (or a simpler tone/loopback bench). Record RX gain, attenuation, RSSI/dBFS, CFO, EVM and BER, and save a reference IQ capture with no gain transitions.
2. **Enable AD9361/AD9363 AGC.** Document the selected gain-control mode and relevant register/`iio_attr` settings. Apply controlled input-level changes with a digital or fixed attenuator to force transitions across gain-table regions/LNA states where practical.
3. **Capture the transition.** Save raw complex IQ before, during and after each gain change, with enough samples on each side for the CFO fit (`--fit-window`, 256 samples by default). Record the actual `sample_index` of each transition in the metadata.
4. **Run the analysis tool** on the real capture and record its `amplitude_step_db`, `phase_discontinuity_deg` and `recovery_samples` per transition — do not hand-estimate these from a plot.
5. **Evaluate modem impact.** EVM/BER/PER around the transition, frame-sync loss/reacquisition if it occurs, comparison against the fixed-gain baseline.

## Report

Use `templates/agc_phase_transition_report.template.md`. It requires, among other fields: exact gain-control settings, the attenuation/input-level sweep, a raw/replayable IQ capture reference, the required plots (gain-state/level vs time, phase error vs time with the fitted CFO trend overlaid, constellation before/during/after), and an explicit statement of whether the observed phase behavior is deterministic, state-dependent or variable across repeats.

## What this lab does not claim

`--self-test` is a synthetic proof of the separation method (CFO trend vs transition-correlated residual), not a hardware result. Real AGC phase-discontinuity evidence requires a real gain-state transition captured on AD9361/AD9363 hardware — this environment does not have that hardware, so no such evidence is claimed here. The lab is hardware-pending until a real capture is analyzed and reported through the template above.
