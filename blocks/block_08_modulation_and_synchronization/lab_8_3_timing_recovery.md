# Lab 8.3 — Symbol Timing Offset and Recovery

## Goal

Inject a timing offset into an oversampled QPSK signal, estimate the best sampling phase and compare EVM/BER before and after timing recovery.

The lab answers the practical question:

> Even when carrier frequency and phase are corrected, how do we choose the correct sample instant for symbol decisions?

## Executable files

| Environment | File | Output |
|---|---|---|
| Python | `blocks/block_08_modulation_and_synchronization/python/lab_8_3_timing_recovery.py` | constellation plots, eye preview, timing search and metrics JSON in `docs/assets` |

Run from the repository root:

```bash
python blocks/block_08_modulation_and_synchronization/python/lab_8_3_timing_recovery.py
```

Generated artifacts:

```text
docs/assets/lab83_timing_constellation_wrong_phase.png
docs/assets/lab83_timing_constellation_recovered.png
docs/assets/lab83_timing_phase_search.png
docs/assets/lab83_timing_eye_preview.png
docs/assets/lab83_timing_metrics.json
```

## Processing chain

```mermaid
flowchart LR
    BITS[Random bits] --> QPSK[QPSK symbols]
    QPSK --> OS[Oversampled waveform]
    OS --> OFFSET[Timing offset]
    OFFSET --> NOISE[Add noise]
    NOISE --> SEARCH[Sampling phase search]
    SEARCH --> BEST[Best phase]
    BEST --> DEC[Hard decisions]
    DEC --> METRICS[EVM and BER]
```

## Timing model

For an oversampled signal with `samples_per_symbol = SPS`, the receiver must choose one sample phase:

```text
phase = 0, 1, 2, ..., SPS-1
```

A wrong phase samples the transition region between symbols and increases EVM/BER. A good phase samples near the stable symbol center.

## Educational timing recovery method

This lab uses a simple phase search:

1. try every sampling phase from `0` to `SPS-1`;
2. sample the received waveform;
3. align scalar gain/phase to the known reference symbols;
4. compute EVM for each phase;
5. choose the phase with minimum EVM.

This is intentionally reference-aided. Real receivers use timing error detectors and tracking loops, for example Gardner or Mueller and Müller methods.

## Metrics

| Metric | Meaning |
|---|---|
| true timing offset | injected timing delay in samples |
| estimated best phase | phase selected by minimum EVM search |
| EVM before | error at intentionally wrong sampling phase |
| EVM after | error at recovered sampling phase |
| BER before | decisions using wrong timing phase |
| BER after | decisions using recovered timing phase |

## Expected plots

- constellation with wrong sampling phase;
- constellation after timing recovery;
- EVM versus sampling phase;
- educational eye preview.

## Common mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| sampling at phase 0 by habit | high EVM even with clean signal | search or track timing phase |
| no oversampling | timing recovery cannot be demonstrated | use SPS > 1 |
| CFO still present | timing estimate becomes unstable | correct CFO first |
| phase offset still present | decisions biased | correct phase before BER |
| wrong reference alignment | EVM curve misleading | compensate delay and scalar gain |

## Report checklist

- [ ] State samples per symbol.
- [ ] State injected timing offset.
- [ ] Explain sampling phase search.
- [ ] Plot EVM versus sampling phase.
- [ ] Include constellation before timing recovery.
- [ ] Include constellation after timing recovery.
- [ ] Include eye preview.
- [ ] Report EVM and BER before/after.
- [ ] Explain how real receivers track timing without reference symbols.

## Engineering conclusion template

```text
The oversampled QPSK signal used SPS = ____ and timing offset ____ samples.
The estimated best sampling phase was ____ samples. EVM improved from ____ % to ____ %,
and BER changed from ____ to ____. The result confirms / does not confirm that timing
selection was the dominant impairment because ______.
```
