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
- **Modem impact, re-measured in the morning with the fixed scripts.** The first, overnight
  modem run was contaminated (a TX toggling loop kept running because board A has no `pkill`) and
  is withdrawn; its files are kept and marked. Re-measured on board B's current image
  (`95c5f010`), 100 frames per static point and 300 per fast-toggling run:
  - static: both AGC modes track the level monotonically (slow_attack 73 -> 63 -> 53 -> 40 dB,
    fast_attack 69 -> 73 -> 63 -> 52 -> 38 dB from TX -40 to 0 dB) and decode better than a fixed
    50 dB, most clearly at the weakest level (TX -40 dB: 5.8e-3 with 4 gross frames fixed,
    1.6e-4 slow_attack, 1.6e-3 fast_attack);
  - TX level toggling every 0.3 s: all three at or below 1e-3;
  - TX level toggling every 5-7 ms: `slow_attack` is the worst (6.6e-3, 11 gross frames; its gain
    hunts between 55 and 68 dB because it needs about 15 ms to settle), fixed gain is in between
    (5.3e-3, 6 gross) and `fast_attack` is the best (2.5e-3, 5 gross). The withdrawn run had the
    same order but a much larger spread (1.7e-2 against 1.9e-3); the clean difference is modest.

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

## Modem results (payload bit errors / bits, re-measured)

Board B image `95c5f010`, Lab 11.45 mode, receive gain readback after 1 s in brackets.
Raw data: [`ad9361-agc-ber-redo-20261014.json`](ad9361-agc-ber-redo-20261014.json),
[`ad9361-agc-ber-fast-toggle-redo-20261014.json`](ad9361-agc-ber-fast-toggle-redo-20261014.json).
The script now refuses to continue if a toggling loop is still running on board A.

| TX gain, dB | manual 50 dB | slow_attack | fast_attack |
|---:|---|---|---|
| -40 | 113/19456 (4 gross) | 4/25344 (73 dB) | 40/24576, 1 gross (69 dB) |
| -30 | 9/24064 | 8/25088 (73 dB) | 5/24832 (73 dB) |
| -20 | 16/24320 | 0/25088 (63 dB) | 0/24320 (63 dB) |
| -10 | 10/24576, 1 gross | 2/23552 (53 dB) | 2/23296 (52 dB) |
| 0 | 32/23296, 1 gross | 6/23296 (40 dB) | 0/22528 (38 dB) |
| toggling -30 <-> -10 every 0.3 s, 100 frames | 24/24064 | 10/24064 | 4/24320 |
| toggling -30 <-> -10 every 5-7 ms, 300 frames | 381/72192, 6 gross | 475/71936, 11 gross (55-68 dB) | 174/69376, 5 gross (49-73 dB) |

The 5-7 ms toggling comes from a shell loop on board A (`sleep 0.005` plus the sysfs write; 100
bare sleeps took 0.52 s), so transitions are frequent but not aligned to the frames.

The overnight run ([`ad9361-agc-ber-20261014.json`](ad9361-agc-ber-20261014.json),
[`ad9361-agc-ber-fast-toggle-20261014.json`](ad9361-agc-ber-fast-toggle-20261014.json)) is invalid
except for its manual-gain column: every slow_attack and fast_attack point ran with an earlier
toggling loop still moving the TX level, which is also why its slow_attack gain readback jumped
between 53 and 73 dB without following the level.

## Limits and next steps

1. Synchronise the TX step with the frame, so that every frame contains a transition at a known
   symbol, to see what a gain change does to Costas and Gardner directly (the 5-7 ms run only
   makes transitions frequent, not aligned).
2. The slow-attack phase step needs either a shared reference between the boards or a single-board
   TX-to-RX loop, where the oscillator wander cancels.
3. Absolute levels need the passive path's S21 (not measured yet).
