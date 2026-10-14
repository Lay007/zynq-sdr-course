# Level steps locked to the frame (#58), two boards, 2026-10-14

Follow-up to [`ad9361-agc-transient-20261014.md`](ad9361-agc-transient-20261014.md). There the TX
level was toggled by a shell loop on board A, so a transition hit a random point of a random frame.
Here the step is written into the transmitted waveform: board A replays a cyclic buffer of
Lab 11.45 frames whose digital amplitude changes by 20 dB at a chosen symbol of the frame. The step
is locked to the frame to the sample. Script:
`blocks/block_11_integrated_sdr_project/python/two_board_agc_frame_step.py`. Raw data:
[`ad9361-agc-frame-step-20261014.json`](ad9361-agc-frame-step-20261014.json).

Bench: board A TX1 -> 30 dB -> splitter -> board B RX1, 915 MHz, TX gain -10 dB, high level = the
usual frame amplitude, low level 20 dB below it. Board B image `8fb3a6a5`, Lab 11.45 differential
mode, 152-symbol frame (preamble symbols 0-23, payload 24-151, 256 payload bits). Manual RX gain
50 dB; the AGC modes start from whatever they settle to.

## Every frame contains a step, up and down in turn, 100 frames per point

Gross = more than 8 payload bit errors in a frame.

| Step at frame symbol | manual: locked / gross | slow_attack | fast_attack |
|---|---|---|---|
| none, high level | 92 / 0 | 93 / 0 | 92 / 0 |
| none, low level | 93 / 0 | 98 / 0 | 97 / 1 |
| 2 (early preamble) | 32 / 0 | 27 / 0 | 54 / 1 |
| 14 (late preamble) | 81 / 47 | 76 / 47 | 86 / 51 |
| 26 (payload start) | 74 / 42 | 80 / 48 | 84 / 46 |
| 60 | 78 / 48 | 86 / 53 | 69 / 41 |
| 96 | 65 / 58 | 66 / 56 | 74 / 44 |
| 136 | 75 / 0 | 76 / 2 | 58 / 3 |
| 148 | 67 / 0 | 72 / 0 | 64 / 1 |

- A step anywhere from the late preamble to the middle of the payload ruins about half of the
  locked frames. The damaged frames lose more bits the earlier the step is (80-90 errors per
  gross frame at symbol 26, about 44 at 60, about 30 at 96): the rest of the frame after the step is lost.
- A step in the early preamble mostly prevents the lock (27-54 of 100 frames lock), but the frames
  that do lock are clean.
- A step in the last 16 symbols costs one to three bit errors per frame (single-bit frames, not
  gross; manual at symbol 148: 224 errors over 67 frames).
- **The three gain modes behave the same.** The level changes every 0.32 ms, faster than either AGC
  can follow, and even manual gain loses the same frames. What fails here is the modem's own
  receive chain, not the AD9361 gain control.

## Which direction: one abrupt step per 8 frames, 300 frames per point, manual gain

The level steps abruptly in one direction at symbol 60 and returns slowly (linear in dB over the
next 8 frames, 2.5 dB per frame). The triangle has the slow ramps and no abrupt step. One received
frame in 8 contains the step.

| Envelope | Locked | Gross | Payload bit errors |
|---|---:|---:|---:|
| step **up** 20 dB, slow return | 286 | 2 | 70 / 73216 |
| step **down** 20 dB, slow return | 279 | **35** | 1157 / 71424 |
| triangle, no step | 283 | 4 | 127 / 72448 |

35 gross frames out of 279 is one in eight: practically every frame that contains a 20 dB step
**down** is lost from the step on, while a step **up** does no harm beyond the triangle baseline.
This explains the "about half" in the first table: the alternating envelope steps down in every
second frame.

## What is and is not known

- Measured: the fabric receive chain of Lab 11.45 does not survive a sudden 20 dB drop of its input
  in the middle of a frame, and does survive the same rise and slow changes of 2.5 dB per frame.
- Assumed, not checked: a loop whose error signal scales with the input amplitude (Costas phase
  detector, Gardner timing detector, or the DC blocker relative to the signal) loses its loop
  gain by 20 dB or more at the drop and cannot hold the residual frequency and timing offsets of
  the two boards for the rest of the frame. A simulation of the chain with the same stepped input
  would show which loop it is.
- For #58 itself: with the level changing every frame the AGC modes neither help nor hurt. The
  earlier 5-7 ms toggling result (fast_attack best, slow_attack worst) is a different regime, where
  the AGC has time to act between steps.
- Not measured here: the slow-attack phase step, which still needs a common reference.
