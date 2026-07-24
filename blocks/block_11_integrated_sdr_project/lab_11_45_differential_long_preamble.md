# Lab 11.45 — Differential QPSK + a longer preamble: the rotation floor, gone

## Goal

Eliminate the residual whole-burst rotation failures that survived the lock-tolerance fix, and beat
the absolute `tol=1` image on BER — without giving up a clean two-board link.

Prerequisites: [Lab 11.42](lab_11_42_ber_floor_lock_tolerance.md) (the false-lock fix that left a
~1% rotation floor) and [Lab 11.43](lab_11_43_dqpsk_model.py) (the differential codec that removes the
rotation ambiguity at the source).

## The arc

1. **The floor is a whole-burst 90° rotation** the frame sync occasionally mis-resolves. `tol=1`
   removed the spurious-lock half; a carrier-marginal half (~1%) remained.
2. **Differential QPSK removes the ambiguity**: the info is the phase *difference* between
   consecutive symbols, so a constant rotation cancels. The codec is proven correct — in a coherent
   fabric loopback with Gardner it decodes at **BER 0**, and it is rotation-invariant offline and in
   RTL.
3. **But on the two-board link it errs at one early-payload symbol** (a cluster at payload index 5 =
   symbol 14). Every isolating test refuted the obvious causes — not the codec (loopback is perfect),
   not the frame data (offline is perfect), not a 180° transition, not the CFO magnitude.
4. **The cause is adaptive-loop transients.** Differential decoding reads the phase difference between
   consecutive symbols, so *any* RX loop still adapting in the early payload — the Costas carrier, the
   DC blocker's running-average convergence, the Gardner timing — perturbs it. The coherent loopback
   is clean precisely because those loops are off. Turning the DC blocker off on the two-board link
   halves the cluster; that was the confirming test.

## Why the preamble was the real lever

The loops acquire during a window that **outlasts the 12-symbol preamble**. From
`tb_qpsk_costas_acq_window`: the freeze gate opens ~16 symbols before the frame, the acquisition runs
`ACQ_SYMBOLS=32`, and the frame sync locks at symbol 31 — i.e. the loops are still slewing ~4 symbols
*into* the payload. In absolute QPSK that is invisible (once locked, each symbol is right); in
differential it corrupts exactly those early-payload symbols.

The clean fix is not to freeze the loops (architecturally impractical — they sit upstream of frame
detection in a continuous, variable-latency stream), but to **start the payload later**: a longer
preamble. And because the frame length and preamble offset are *runtime* parameters
(`symbol_count`, `preamble_count`) and the ROM already holds 512 bits, this needs **no bitstream
change at all**:

- frame = the ROM's first **304 bits** = a 24-symbol preamble + the same 256-bit payload;
- run with `symbol_count=152`, `preamble_bits=48`;
- the on-chip correlator still locks on the first 24 bits (unchanged, no false peaks); the payload now
  begins at symbol 24, past the acquisition transient.

`make_long_preamble_frame()` builds it; the diff frame still wraps cleanly (total phase increment 0
mod 4).

## Result (two-board, A TX1 → 30 dB → B RX1)

| | absolute `tol=1` (140/24) | **differential, 24-sym preamble (152/48)** |
|---|---|---|
| payload BER | ~3×10⁻³ | **~4×10⁻⁴** (≈7–13× better) |
| gross (whole-burst rotation) | 0.75% | **0** |
| clean frames | 98.9% | 96.9–98.8% |
| rotation-invariant | no | **yes** |

**The rotation floor is gone — gross is 0 across every run** — and BER drops an order of magnitude
because no burst decodes at ~46% any more. The clean-frame rate is comparable: a residual intermittent
single-bit cluster (now near payload index 19) remains, which is the inherent ~3 dB differential
penalty, not a rotation failure. Result: `docs/assets/lab1145_diff_long_preamble_live.json`.

Longer still is worse: a 32-symbol preamble dropped the lock rate (the frame plus its
`RX_SAMPLE_MARGIN` ran past the sampler window). 24 symbols is the operating point.

## What this lab is really about

Two fixes were on the table for the differential transient. Freezing the adaptive loops after the
preamble is the textbook answer, but it is architecturally impractical here: the loops are upstream of
frame detection, the two-board stream is continuous (no signal-present boundary), and the frame
latency varies — so there is no timely "preamble done" signal to hand them. Lengthening the preamble
achieves the same end (the payload starts settled) with a runtime parameter and no new logic. The
cheaper fix was not the smaller idea; it was the one that fit the architecture.
