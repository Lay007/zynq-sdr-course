# Lab 8.9 — QPSK carrier recovery

## Goal

Correct the CFO that turns a QPSK constellation into a ring, using a decision-directed Costas loop, and resolve the remaining `90°` ambiguity.

## Algorithm

For each symbol, the loop:

1. de-rotates the sample by the negative NCO phase estimate;
2. computes the QPSK phase error;
3. updates the integral frequency estimate;
4. updates phase through a proportional-integral filter.

```text
y = s · exp(-jθ)
e = sign(Re(y))·Im(y) - sign(Im(y))·Re(y)
freq += ki·e
θ += freq + kp·e
```

The loop aligns the clusters with the QPSK decision grid, but it can acquire any `k·90°` orientation. A known preamble tests all four rotations and selects the correct bit labeling.

## Reproduce

```bash
python blocks/block_08_modulation_and_synchronization/python/qpsk_carrier_recovery.py
```

Expected result:

- BER is near random decisions before correction;
- four compact clusters remain after loop acquisition;
- the NCO estimate follows the CFO phase ramp;
- BER is zero across the reference sweep after ambiguity resolution.

This lab completes the Block 8 QPSK route and prepares the carrier-recovery algorithm for streaming RTL.
