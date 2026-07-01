# Lab 8.9 — QPSK carrier recovery (decision-directed Costas loop)

## Goal

[Lab 8.8](lab_8_8_qpsk_modem_and_impairments.md) ended with the open problem: an uncorrected
**carrier frequency offset (CFO)** rotates every QPSK symbol by a growing phase, smearing the
four constellation points into a **ring** that the hard decision cannot read (BER ≈ 0.5). This
lab closes it with a **carrier-recovery loop** that de-rotates the ring back into four points,
and shows the one twist that BPSK does not have — a residual **90° phase ambiguity**.

## The loop

The recovery is a **decision-directed Costas loop**: a streaming feedback loop with exactly the
structure you would put on the FPGA (an NCO phase accumulator + a proportional-integral loop
filter + a phase-error detector), the frequency-domain twin of the Gardner timing loop.

Per symbol `s`:

```
y = s · e^(−jθ)                      # de-rotate by the current NCO phase
e = sign(Re y)·Im y − sign(Im y)·Re y   # decision-directed QPSK phase error
freq += ki·e                         # integral term tracks the CFO
θ    += freq + kp·e                  # proportional term tracks the phase
```

The phase-error detector `e` is zero when `y` sits on a QPSK point and pushes `θ` toward the
nearest one otherwise, so the loop drives the ring onto the constellation grid. The integral
term `freq` accumulates into a constant slope that **matches the CFO ramp** — the bottom-left
panel below shows the NCO phase climbing along exactly that ramp.

![QPSK carrier recovery](https://lay007.github.io/zynq-sdr-course/assets/qpsk_carrier_recovery.png)

- **Received (ring)** — QPSK + CFO, BER ≈ 0.5, undecodable.
- **After Costas + preamble de-rotation** — four clean clouds; CFO gone.
- **NCO phase** — locks onto the CFO ramp within a few tens of symbols.
- **BER vs CFO** — without recovery BER pins at chance for any non-zero CFO; with the loop it
  stays at 0 across the whole sweep.

## The 90° ambiguity

A QPSK Costas loop error detector is happy on *any* of the four constellation points, so it
locks to one of four `k·90°` rotations — and which one is arbitrary. The ring becomes four
clean points, but the absolute I/Q labelling may be rotated, scrambling the bits (BER 0.25–0.5)
even though the *constellation* looks perfect. This is why a raw Costas BER-vs-CFO curve jumps
around.

The fix is the same **known preamble / unique word** the BPSK modem already uses for frame sync
(the 8-bit lock word of [Lab 8.8](lab_8_8_qpsk_modem_and_impairments.md) /
[Block 11](../block_11_integrated_sdr_project/README_en.md)): try the four rotations, keep the
one that matches the preamble. That is what turns the noisy curve into the flat **BER = 0** line
above. (Differential QPSK encoding is the alternative — it removes the ambiguity without a
preamble, at a ~2× BER penalty.)

## Reproduce

```bash
python blocks/block_08_modulation_and_synchronization/python/qpsk_carrier_recovery.py
# -> raw BER @ CFO=0.01: 0.5005 | recovered: 0.0
```

## Next steps

- **RTL**: port this loop to `qpsk_costas_carrier_recovery.v` (NCO + PI + the same
  decision-directed detector, complex de-rotate via CORDIC / sin-cos LUT) so over-the-air QPSK
  de-rotates on-chip, mirroring how the Gardner timing loop ported.
- **Hardware**: drop the QPSK modem into the runtime AD9361 bridge for QPSK BER = 0 in digital
  loopback (no CFO there, so carrier recovery is bypassed), then enable this loop for the
  over-the-air four-point constellation of [Lab 8.7](lab_8_7_real_hardware_bpsk_metrics.md).
