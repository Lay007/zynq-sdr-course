# Lab 8.4 - End-to-End Synchronization Chain

## Goal

Combine timing offset, carrier frequency offset, phase offset and noise in one synthetic QPSK link, then recover the signal using a staged synchronization chain.

The lab answers the practical question:

> How do timing recovery, CFO correction and phase correction work together in a complete receiver chain?

## Executable files

| Environment | File | Output |
|---|---|---|
| Python | `blocks/block_08_modulation_and_synchronization/python/lab_8_4_end_to_end_sync_chain.py` | stage constellations, EVM/BER summaries and metrics JSON in `docs/assets` |

Run from the repository root:

```bash
python blocks/block_08_modulation_and_synchronization/python/lab_8_4_end_to_end_sync_chain.py
```

Generated artifacts:

```text
docs/assets/lab84_sync_constellation_raw.png
docs/assets/lab84_sync_constellation_after_timing.png
docs/assets/lab84_sync_constellation_final.png
docs/assets/lab84_sync_timing_search.png
docs/assets/lab84_sync_evm_stages.png
docs/assets/lab84_sync_ber_summary.png
docs/assets/lab84_sync_chain_metrics.json
```

## Processing chain

```mermaid
flowchart LR
    BITS[Random bits] --> QPSK[QPSK symbols]
    QPSK --> OS[Oversampled waveform]
    OS --> IMP[Timing + CFO + phase + noise]
    IMP --> TIMING[Timing phase search]
    TIMING --> CFO[CFO estimation/correction]
    CFO --> PHASE[Phase correction]
    PHASE --> DEC[Hard decisions]
    DEC --> METRICS[EVM and BER]
```

## Staged receiver

The educational receiver applies synchronization in this order:

1. **Timing phase search** - select the sampling phase with the strongest decimated symbol energy.
2. **CFO estimation/correction** - estimate residual frequency slope using known reference symbols.
3. **Phase correction** - remove remaining constant constellation rotation.
4. **Hard decisions** - convert corrected symbols to bits.
5. **Metrics** - compute EVM and BER before and after synchronization.

## What to expect

The default run (deterministic, as printed by the script) gives:

```text
Timing offset true/estimated: 3/6 samples
CFO true/estimated/error: 1350.000/1349.996/-0.004 Hz
Phase true/estimated/error: 0.550000/0.600344/-0.000550 rad
EVM raw/timing/CFO/final: 3413.163/19524.022/4.857/4.857 %
BER raw/final: 5.141602e-01/0.000000e+00
```

How to read the stage table:

- **The first two EVM values (3413 % and 19524 %) are not "errors of 34x and 195x".** Both
  are far above 100 %, which means the constellation is still rotating (CFO not yet
  removed) and the scalar alignment has nothing stable to lock to. The EVM number only
  becomes meaningful after the CFO stage (4.857 %). The interesting drop is BER, from
  0.514 (a coin flip) to 0.
- **The estimated timing phase (6) differs from the injected offset (3) and that is
  fine.** As in [Lab 8.3](/zynq-sdr-course/en/labs/lab-8-3-timing-recovery/), with
  rectangular pulses every phase inside the flat part of the symbol is correct; the
  stage only has to avoid the samples belonging to the neighbouring symbol.
- **CFO error is -0.004 Hz on 1350 Hz**: a fit over thousands of known symbols is very
  precise in a synthetic model with a flat symbol. Real captures will not be this good.
- **"EVM after CFO" and "EVM final" are identical (4.857 %).** These EVM values are computed
  after a scalar gain/phase alignment to the reference, which absorbs any *constant* phase, so
  the phase stage cannot change them. BER, however, is scored on the receiver's own output with
  no such alignment, so a wrong phase estimate would show up there as bit errors.
- **The estimated phase is 0.600 rad, not the injected 0.55, and that is correct.** The receiver
  samples at phase 6, and the 1350 Hz CFO rotates the signal by `2*pi*1350*6/1e6 = 0.051 rad` over
  those 6 samples. Referenced to the sampling instant, the phase error is only -0.0006 rad.

## Impairments in the model

| Impairment | Meaning |
|---|---|
| timing offset | receiver samples at the wrong point inside the symbol interval |
| CFO | constellation rotates over time |
| phase offset | constellation has a constant rotation |
| noise | spreads constellation points and limits EVM/BER |

## Metrics

| Metric | Meaning |
|---|---|
| estimated timing phase | selected sample phase from timing search |
| estimated CFO | measured frequency offset after timing selection |
| CFO error | estimated CFO minus true CFO |
| estimated phase | measured residual phase after CFO correction |
| EVM raw | error before synchronization |
| EVM after timing | error after choosing the sampling phase |
| EVM after CFO | error after frequency correction |
| EVM final | error after full synchronization |
| BER raw/final | decision quality before and after the full chain |

## Why this closes Block 8

Labs 8.1-8.3 isolate individual synchronization problems. Lab 8.4 combines them into a receiver chain:

| Previous lab | Role in Lab 8.4 |
|---|---|
| Lab 8.1 CFO | frequency correction stage |
| Lab 8.2 phase | final constellation rotation correction |
| Lab 8.3 timing | sampling phase selection |
| Lab 7.3 loopback metrics | EVM/BER reporting style |

## Limitations

This is still an educational model. A production receiver would additionally need:

- frame synchronization;
- preamble detection;
- non-data-aided tracking loops;
- sample-rate offset tracking;
- pulse shaping with matched filtering;
- IQ imbalance correction;
- robust operation at lower SNR.

## Report checklist

- [ ] State all injected impairments.
- [ ] Explain the staged receiver order.
- [ ] Include raw constellation.
- [ ] Include constellation after timing recovery.
- [ ] Include final constellation.
- [ ] Include EVM by stage.
- [ ] Include BER before/after.
- [ ] State remaining limitations before real RF use.

## Engineering conclusion template

```text
The synthetic receiver used timing offset ____ samples, CFO ____ Hz and phase offset ____ rad.
The staged synchronizer estimated timing phase ____, CFO ____ Hz and phase ____ rad.
EVM improved from ____ % to ____ %, while BER changed from ____ to ____.
This closes / does not close the basic synchronization chain because ______.
```
