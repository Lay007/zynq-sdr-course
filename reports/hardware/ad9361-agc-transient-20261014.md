# AD9361 receive AGC: gain-step transients and modem impact, two boards, 2026-10-14

## Result

Board A sent a tone, then the modem frame, to board B through a conducted path, and stepped its TX
gain by 20 dB while board B recorded continuously. Three receive gain modes were compared:
manual (the control), `slow_attack` and `fast_attack`.

- **The transmitter's own 20 dB attenuation step shifts the phase by about 1.2 degrees**
  (+1.0 / +1.3 / +1.2 up, -1.3 / -1.1 / -1.3 down), reproducibly, against a 0.1-0.3 degree floor.
  Any receiver-side phase effect has to be read against this.
- **`fast_attack` changes the receive gain within 0.04-0.12 ms and adds a phase step that depends on
  the gain transition**: -10.7, -5.8 and +0.2 degrees for the up steps, +1.7 and +0.2 degrees for
  the down steps, against a floor of at most 1 degree. Its final gain is not reproducible: the same
  input ended at 46, 51 and 53 dB, and the same starting input gave 72, 61 and 66 dB. This matches
  the AD9361 fast-attack behaviour of locking the gain once it has acquired.
- **`slow_attack` settles in 14-17 ms**, from 69-70 dB to 46 dB and back, the same in every repeat.
  On the up step 0.46-0.63 % of the samples clip while it settles. Its phase step **could not be
  resolved**: over a 15 ms gap the phase between the two boards' independent oscillators wanders by
  5-14 degrees RMS, which is as large as the measured steps (-9 to -16, +13 to +31 degrees).
- **Correction (same night): most of the modem measurements below are invalid.** The scripts
  stopped board A's background processes with `pkill`, which board A's BusyBox does not have, so
  the TX-gain toggling loop of each dynamic run kept running after it. Every point measured after
  the first dynamic run had board A's TX gain jumping between -30 and -10 dB underneath it. Valid:
  the manual-gain static points and the manual-gain 0.3 s dynamic run (they ran before or as the
  first loop). Invalid: all `slow_attack` and `fast_attack` modem points, and the whole 5-7 ms
  run, which also had the three earlier loops running. The earlier conclusion that the 5-7 ms run
  "reverses the order" (slow_attack worst, fast_attack best) is withdrawn. The transient
  measurements above ran before any loop existed and are not affected. The scripts now stop
  processes by PID (commit `c5997c4`); the modem part has to be re-measured.

## Setup

| Parameter | Value |
|---|---|
| RF chain | A TX1 -> variable attenuator 0 dB -> 30 dB fixed -> 3-way splitter -> B RX1 (other ports: RTL-SDR, 50 ohm) |
| Boards | A: vendor image with the DDS/DMA core; B: course image `69023a2b` (Lab 11.45) |
| Carrier / sample rate | 915 MHz / 3.84 MS/s on both boards; inter-board offset measured as about -418 Hz |
| Transient signal | tone at +300 kHz (a 3840-sample cyclic buffer, 300 whole cycles), about -3 dBFS at the DAC |
| Step | TX gain -30 dB <-> -10 dB, 0.2 s into a 2,000,000-sample `iio_readdev` capture (65,536-sample buffers) |
| Repeats | 3 per mode and direction |
| Modem signal | Lab 11.45 frame, mode `0x3f630`; 60 frames per point |
| Scripts | `blocks/block_11_integrated_sdr_project/python/two_board_agc_step_transient.py`, `two_board_agc_ber.py` |
| Raw data | [`ad9361-agc-step-transient-20261014.json`](ad9361-agc-step-transient-20261014.json), [`ad9361-agc-ber-20261014.json`](ad9361-agc-ber-20261014.json) |

## Method

The capture is first checked for gaps: across the DMA buffer boundaries before the step, the
tone's residual phase must not jump more than at random positions (it did not: boundary steps up to
0.026 rad against a 99th percentile of 0.032 rad on a strong tone; one dropped sample would be
0.49 rad).

The tone frequency is estimated on the pre-step region and removed. The step is located as the
largest change of the smoothed envelope. The amplitude settling time is the first instant after
which the envelope stays within 1 dB of its final level for 2000 samples. The phase step is the
difference of two linear fits, 3000 samples each, taken just before the step and just after it has
settled, both extrapolated to the middle of the gap. The floor is the same measurement repeated at
20 places before the step with the same gap, where no step exists. A first version measured the
phase over windows tens of milliseconds apart and reported -13 to +29 degrees for the manual
control: that was oscillator wander, not a step, which is why the floor is reported now.

## Transient results

| Mode | Direction | RX gain before -> after, dB | Envelope change, dB | Settling, ms | Phase step, deg | Floor RMS, deg | Clipped, % |
|---|---|---|---:|---:|---:|---:|---:|
| manual | up | 50 -> 50 (x3) | +19.9 | < 0.04 | +1.0, +1.3, +1.2 | 0.2 | 0 |
| manual | down | 50 -> 50 (x3) | -19.9 | < 0.04 | -1.3, -1.1, -1.3 | 0.1-0.3 | 0 |
| slow_attack | up | 70/69 -> 46 | -0.4 to +0.7 | 15.0-16.5 | -8.8, -15.5, -11.7 | 5.5-7.3 | 0.46-0.63 |
| slow_attack | down | 46 -> 69 | -0.7 | 14.3-16.8 | +13.3, +30.6, +25.1 | 13.4-14.4 | 0 |
| fast_attack | up | 72 -> 46, 61 -> 51, 66 -> 53 | -2.2, +13.3, +7.5 | 0.04 | -10.7, -5.8, +0.2 | 0.1-0.3 | < 0.001 |
| fast_attack | down | 53 -> 68, 52 -> 67 | -5.5 | 0.09-0.12 | +1.7, +0.2 | 0.8-1.0 | 0 |

The third fast-attack down run is excluded: its envelope took 5.9 ms to settle and the phase unwrap
failed across it (raw values kept in the JSON with `valid: false`).

## Modem results (payload bit errors / bits)

**Only the manual-gain column is valid** (see the correction above); the other cells are kept
because they are the raw record, marked as contaminated.

| TX gain, dB | manual 50 dB | slow_attack (invalid) | fast_attack (invalid) |
|---:|---|---|---|
| -40 | 43/12544 (1 gross) | 2/14336 | 2/14848 |
| -30 | 55/14592 (2 gross) | 0/14592 | 8/14848 |
| -20 | 10/14592 (1 gross) | 0/14080 | 2/15104 |
| -10 | 0/14592 | 10/14848 | 0/14080 |
| 0 | 8/14080 | 9/14080 | 2/15104 |
| toggling -30 <-> -10 every 0.3 s | 10/14848 | 2/13824 (invalid) | 6/14848 (invalid) |
| toggling every 5-7 ms, 300 frames (whole run invalid) | 399/69120 (7 gross) | 1104/66560 (24 gross) | 135/72192 (3 gross) |

The 5-7 ms run comes from a shell loop on board A (`sleep 0.005` plus the sysfs write; 100
iterations of the bare sleep took 0.52 s). Raw data:
[`ad9361-agc-ber-fast-toggle-20261014.json`](ad9361-agc-ber-fast-toggle-20261014.json). Under a fixed
gain the static points average about 1.9e-3 for these two levels; this comparison is withdrawn
together with the run.

The receive gain readback under `slow_attack` was 53 dB at TX -40 dB, 73 dB at -30 and -20 dB and
53 dB again at -10 and 0 dB. That pattern is explained by the leftover toggling loop moving the
real input level underneath the static points, not by the AGC.

## Limits and next steps

0. Re-measure the AGC modem points with the fixed scripts (every loop stopped by PID).
1. Synchronise the TX step with the frame, so that every frame contains a transition at a known
   symbol, to see what a gain change does to Costas and Gardner directly (the 5-7 ms run only
   makes transitions frequent, not aligned).
2. The slow-attack phase step needs either a shared reference between the boards or a single-board
   TX-to-RX loop, where the oscillator wander cancels.
3. Absolute levels need the passive path's S21 (not measured yet).
