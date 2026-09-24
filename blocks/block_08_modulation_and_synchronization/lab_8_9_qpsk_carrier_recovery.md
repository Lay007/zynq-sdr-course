# Lab 8.9 — QPSK carrier recovery (decision-directed Costas loop)

## Goal

[Lab 8.8](/zynq-sdr-course/en/labs/lab-8-8-qpsk-modem-impairments/) ended with the open problem: an uncorrected
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

![QPSK carrier recovery](/zynq-sdr-course/assets/qpsk_carrier_recovery.png)

- **Received (ring)** — QPSK + CFO, BER ≈ 0.5, undecodable.
- **After Costas + preamble de-rotation** — four clean clouds; CFO gone.
- **NCO phase** — locks onto the CFO ramp within about a hundred symbols at the plotted offset of 0.01 cycles/symbol (larger offsets take longer, see below).
- **BER vs CFO** — without recovery BER pins at chance for any non-zero CFO; with the loop it
  stays at 0 across the whole sweep.

## The 90° ambiguity

A QPSK Costas loop error detector is happy on *any* of the four constellation points, so it
locks to one of four `k·90°` rotations — and which one is arbitrary. The ring becomes four
clean points, but the absolute I/Q labelling may be rotated, scrambling the bits (BER 0.25–0.5)
even though the *constellation* looks perfect. This is why a raw Costas BER-vs-CFO curve jumps
around.

The fix is the same **known preamble / unique word** the BPSK modem already uses for frame sync
(the 8-bit lock word of [Lab 8.8](/zynq-sdr-course/en/labs/lab-8-8-qpsk-modem-impairments/) /
[Block 11](/zynq-sdr-course/en/blocks/11-integrated-sdr-project/)): try the four rotations, keep the
one that matches the preamble. That is what turns the noisy curve into the flat **BER = 0** line
above. The script uses 32 known symbols as that preamble and scores BER only on the symbols after
it. (Differential QPSK encoding is the alternative — it removes the ambiguity without a
preamble, at a ~2× BER penalty.)

## Reproduce

```bash
python blocks/block_08_modulation_and_synchronization/python/qpsk_carrier_recovery.py
# -> one line per CFO point (see What to expect), then
# -> raw BER @ CFO=0.01: 0.5005 | recovered: 0.0
```

## What to expect

The BER-vs-CFO sweep sends 20 000 symbols per point at Eb/N0 = 12 dB, skips the first 1000 symbols, uses the next 32 known symbols as the preamble that picks the 90-degree rotation, and scores the remaining 37 936 bits. It also prints the pull-in time: the symbol index after the last symbol error, measured against the known data.

| CFO, cycles/symbol | 0 - 0.004 | 0.006 | 0.008 | 0.010 | 0.012 | 0.014 | 0.016 | 0.018 | 0.020 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| pull-in, symbols | 0 | 21 | 68 | 95 | 315 | 268 | 477 | 384 | 650 |
| raw BER | 0 at CFO 0, else about 0.50 | 0.50 | 0.50 | 0.50 | 0.50 | 0.50 | 0.50 | 0.50 | 0.50 |
| recovered BER | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

- **Recovered BER is 0 at every point**, over 37 936 bits each, so the claim is "below about 1e-4 per point", not "error-free".
- **Pull-in grows steeply with the offset**, and not smoothly: about 100 symbols at the plotted 0.01 cycles/symbol, 650 at 0.02. Beyond the loop's lock range the loop acquires by slipping cycles until the integrator catches up, and the number of slips depends on the noise.
- **The 1000-symbol skip is not free.** It is what keeps the preamble outside the pull-in phase. The exercises show what happens when it is shorter.

## Exercises

1. In `ber_vs_cfo()` change the skip from 1000 to 100 symbols. Up to 0.010 cycles/symbol nothing changes, but from 0.012 up the recovered BER becomes 0.996, 0.997, 0.501, 6.95e-3 and 0.987. The preamble now falls inside the pull-in phase: the rotation it picks is right for that moment and wrong for the locked payload (a BER near 1 is a 180-degree error, near 0.5 a 90-degree one). A real receiver must place the preamble after the loop has locked, or run the loop on a long enough training sequence first.
2. Double the loop gains (`kp=0.04, ki=0.004`): pull-in drops to 0 up to 0.012 cycles/symbol and to 211 symbols at 0.02. Halve them (`kp=0.01, ki=0.001`): pull-in reaches 546 symbols at 0.01 and 5643 at 0.02, and from 0.012 up even the 1000-symbol skip is too short (recovered BER 0.997, 2.5e-2, 0.500, 0.950, 0.120). What does a wider loop cost you in return? Measure the recovered EVM at CFO = 0 for both gain settings.
3. Change `resolve_90deg_ambiguity()` to choose the rotation by the lowest BER over the whole frame, as an earlier version of this script did. Explain why the sweep result does not change here, and why that choice is still wrong for a receiver: it uses the payload as its own reference.
4. Differential QPSK removes the ambiguity without a preamble. Explain where its roughly 2x BER penalty comes from.

## Next steps

- **RTL**: this loop is ported to `blocks/block_05_fpga_hdl_flow/rtl/qpsk_costas.v` (NCO + PI +
  the same decision-directed detector, a complex de-rotate at symbol rate), placed between the
  symbol sampler and the hard decision. It de-rotates the four-point constellation on-chip and is
  exercised by the `tb_qpsk_rx_costas` and `tb_qpsk_costas_stress` testbenches, mirroring how the
  Gardner timing loop ported.
- **Hardware**: the loop is part of the in-fabric receiver validated over the air in
  [Lab 11.4](/zynq-sdr-course/en/labs/lab-11-4-final-measurement-report/), where differential QPSK plus a preamble
  removes the `90°` ambiguity ([Lab 11.45](/zynq-sdr-course/en/labs/lab-11-45-differential-long-preamble/)).
  For the raw over-the-air constellation seen from an independent receiver, compare with
  [Lab 8.15](/zynq-sdr-course/en/labs/lab-8-15-real-hardware-bpsk-metrics/).
