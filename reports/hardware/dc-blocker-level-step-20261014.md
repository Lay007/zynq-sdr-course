# The DC blocker loses the frame after a level drop, 2026-10-14

Follow-up to [`ad9361-agc-frame-step-20261014.md`](ad9361-agc-frame-step-20261014.md). There, a
sudden 20 dB drop in the middle of a frame lost the rest of the frame under every gain mode, while
the same rise did no harm. This report finds the block responsible: the receiver's DC blocker. Raw
data: [`dc-blocker-level-step-20261014.json`](dc-blocker-level-step-20261014.json).

Bench and settings as in the frame-step report: two boards, conducted path, 915 MHz, TX -10 dB,
manual RX gain 50 dB, board B image `8fb3a6a5`, Lab 11.45 differential mode. The only change
between the columns below is the DC blocker enable (`gp_ctrl[9]`, mode bit `0x200`); no bitstream
change.

## Suspect

`dc_blocker.v` estimates the DC offset as the running mean of everything since the frame start,
which turns into a leaky mean with a time constant of 1024 samples (128 symbols, most of a frame)
once enough samples have arrived. It is reset at every frame start. The mean of the signal itself is
not zero over such windows. The differential preamble repeats one symbol for several symbols, and the
receiver usually starts inside the tail of the previous frame. A float model of the running mean on
the transmitted frame puts the estimate at symbol 60 at about 7 % of the strong signal's RMS. After a
20 dB drop that is about 70 % of the weak signal, subtracted from every sample for the rest of the
frame. Before a 20 dB rise, the blocker has learned its offset on the weak signal, and that offset
is under 1 % of the strong signal that follows.

## Silicon: one abrupt drop per 8 frames, symbol 60, 300 frames

| | DC blocker on | DC blocker off |
|---|---|---|
| Drop 20 dB, slow return: locked / gross | 279 / **35** | 298 / **4** |
| Triangle, no abrupt step: locked / gross | 283 / 4 | 298 / 2 |

With the DC blocker off, the drop costs nothing beyond the triangle baseline.

## Silicon: steady levels, 300 frames

| Level | DC blocker on: locked / clean / payload bit errors | DC blocker off |
|---|---|---|
| High (the usual frame level) | 284 / 278 / 21 | **300 / 299 / 1** |
| Low (20 dB below) | 283 / 259 / 318 (7 gross) | **299 / 297 / 4** |
| Triangle (slow 20 dB ramps) | 287 / 267 / 107 | 297 / 291 / 83 |

The DC blocker costs frames and bits on this bench even without any step: more frames fail to lock,
and there are more single-bit errors. The second effect matches what `dc_blocker.v` already records
about its earlier short-time-constant version. The leakage DC the block was built for comes from a
single board's own TX leaking into its RX (Lab 11.26 self-OTA). On the conducted two-board link it is
apparently small enough for the AD9361's own DC correction.

## Simulation: the same receiver RTL with a level step

`tools/run_qpsk_level_step_sim.py` runs `tb_qpsk_level_step.v`: `qpsk_zynq_ber_top` with the
parameters of the gpreg bridge, in the Lab 11.45 mode. Its input comes from
`blocks/block_05_fpga_hdl_flow/python/gen_qpsk_level_step.py`: the transmitted frame with a 20 dB
step at symbol 60, a carrier offset and white noise. `prev` is how many samples of the preceding
strong frame the receiver sees before the first full frame. Payload bit errors of the locked
frame; "lost" means the frame did not lock or ended early.

| CFO | prev | Drop, DC on | Drop, DC off | Rise, DC on | Rise, DC off |
|---:|---:|---|---|---|---|
| 0 Hz | 0 | 0 | 0 | 0 | 0 |
| 0 Hz | 400 | lost (40 symbols) | 0 | 0 | 0 |
| 0 Hz | 900 | **62** | 0 | 0 | 0 |
| 500 Hz | 0 | 2 | 0 | 0 | 0 |
| 500 Hz | 400 | lost (no lock) | 0 | 2 | 0 |
| 500 Hz | 900 | **60** | 0 | 0 | 0 |
| 3 kHz | 0 | **55** | 9 | lost (90 symbols) | 0 |
| 3 kHz | 400 | **77** | 0 | 0 | 0 |
| 3 kHz | 900 | **75** | 0 | 5 | 1 |

The simulation reproduces the asymmetry: with the DC blocker on, a drop breaks the frame in 7 of 9
conditions; with it off, 8 of 9 are clean. How badly it breaks depends on how much strong signal the
blocker has averaged before the drop (`prev`), which on the board is random from frame to frame.

## Conclusions

- Measured on silicon and reproduced in simulation: the DC blocker, not the gain control and not the
  carrier or timing loops, makes the receiver lose a frame after a sudden level drop.
- Measured on silicon, one session and one pair of boards: on the conducted two-board link the Lab
  11.45 mode decodes better with the DC blocker off, at steady levels too.
- Not done: no RTL change. Possible directions, not tried:
  - keep the DC estimate across frames instead of resetting it;
  - estimate the DC only before the frame;
  - for the two-board link, document the mode without `0x200`.
