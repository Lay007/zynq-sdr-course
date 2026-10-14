# Two-board sensitivity of the Lab 11.45 receiver at 915 MHz, 2026-10-14

Bench: board A TX1 -> 30 dB -> 3-way splitter -> board B RX1, conducted (board A RX1 on another
output, the third output open). Board A replays the Lab 11.45 long differential QPSK frame
(cyclic `iio_writedev`) and steps its TX attenuator in 5 dB steps. That attenuator was measured to
follow its setting to about 0.5 dB ([ad9361-gain-steps-20261014.md](ad9361-gain-steps-20261014.md)),
so the TX setting is a reliable *relative* input level. Board B runs the course image `3d492301`
(mode `0x2D630`, DC blocker persistent, #66) and decodes 100 frames per point in the fabric.
Script: `blocks/block_11_integrated_sdr_project/python/two_board_sensitivity.py`. Raw data:
[`two-board-sensitivity-20261014.json`](two-board-sensitivity-20261014.json). One run per
configuration.

Columns: frames locked (all 152 symbols received), clean (0 payload errors), gross (more than
8 of 256 payload bits wrong), payload BER over the locked frames. RSSI is the AD9361 reading in dB
(a larger number means a weaker signal).

## Board B at manual gain 71 dB

| TX dB | locked | clean | gross | BER | RSSI |
|---:|---:|---:|---:|---:|---:|
| -10 | 96 | 86 | 0 | 1.3e-3 | 80.0 |
| -15 | 99 | 99 | 0 | 0 | 80.0 |
| -20 | 100 | 99 | 1 | 1.1e-3 | 84.3 |
| -25 | 100 | 100 | 0 | 0 | 89.0 |
| -30 | 100 | 97 | 2 | 1.8e-3 | 94.3 |
| -35 | 100 | 100 | 0 | 0 | 99.3 |
| -40 | 100 | 100 | 0 | 0 | 104.0 |
| -45 | 100 | 99 | 0 | 7.8e-5 | 109.3 |
| -50 | 98 | 94 | 2 | 2.3e-3 | 113.8 |
| -55 | 89 | 39 | 8 | 1.4e-2 | 117.3 |
| -60 | 29 | 0 | 29 | 1.3e-1 | 120.3 |
| -65 | 2 | 0 | 2 | 2.9e-1 | 121.0 |
| -70 | 0 | 0 | 0 | - | 121.8 |

## Board B at manual gain 50 dB

| TX dB | locked | clean | gross | BER | RSSI |
|---:|---:|---:|---:|---:|---:|
| -10 | 100 | 100 | 0 | 0 | 72.5 |
| -20 | 100 | 100 | 0 | 0 | 82.5 |
| -30 | 100 | 99 | 0 | 7.8e-5 | 92.5 |
| -35 | 99 | 98 | 1 | 5.2e-3 | 96.8 |
| -40 | 91 | 81 | 6 | 1.0e-2 | 102.0 |
| -45 | 89 | 53 | 16 | 3.8e-2 | 104.3 |
| -50 | 73 | 12 | 34 | 5.1e-2 | 105.0 |
| -55 | 15 | 0 | 15 | 1.3e-1 | 105.0 |
| -60 | 5 | 0 | 5 | 3.8e-1 | 105.0 |
| -70 | 0 | 0 | 0 | - | 105.0 |

(-15 and -25 dB: 100 locked, 100 and 99 clean; full rows in the JSON.)

## Board B with slow-attack AGC

| TX dB | AGC gain | locked | clean | gross | BER | RSSI |
|---:|---:|---:|---:|---:|---:|---:|
| -10 | 54 | 100 | 99 | 1 | 6.6e-4 | 73.8 |
| -20 | 64 | 100 | 100 | 0 | 0 | 84.3 |
| -30 | 73 | 100 | 100 | 0 | 0 | 94.3 |
| -40 | 73 | 100 | 98 | 1 | 1.9e-3 | 104.5 |
| -45 | 73 | 99 | 98 | 0 | 7.9e-5 | 109.3 |
| -50 | 73 | 97 | 93 | 0 | 3.2e-4 | 113.8 |
| -55 | 73 | 91 | 45 | 11 | 1.4e-2 | 117.3 |
| -60 | 73 | 39 | 0 | 37 | 8.5e-2 | 120.3 |
| -65 | 73 | 4 | 0 | 4 | 3.1e-1 | 121.5 |
| -70 | 73 | 0 | 0 | 0 | - | 122.3 |

## What it shows

- **Threshold.** At high gain (manual 71 or AGC at 73) the receiver gives at least 93 clean frames
  out of 100 down to TX -50 dB. Between -50 and -55 dB the clean count falls to about 40, at
  -60 dB no frame is clean, at -70 dB nothing locks. The cliff is about 10 dB wide, as expected
  for an uncoded receiver whose preamble detector and loops lose lock together.
- **Lock outlives the payload.** At -55 dB about 90 frames still lock but more than half carry
  errors; at -60 dB the frames that lock are almost all gross. A "locked" count alone overstates
  the margin; the payload check (or the packet CRC of Lab 11.46) is the real criterion.
- **Gain 50 dB costs about 10-15 dB of sensitivity.** The clean count drops below 90 already at
  -40 dB. The RSSI stops at 105 from -50 dB down: at this gain the noise of the later stages and
  the ADC sets the floor, not the input noise. Manual gain must be high for weak signals.
- **Gain 71 dB overloads at the strong end.** At -10 dB, 86 clean and BER 1.3e-3, and the RSSI does
  not change between -10 and -15 dB (80.0 both). At gain 50 the same input is clean.
- **Slow-attack AGC gives the widest range:** at least 93 clean from -10 to -50 dB (40 dB of
  input range in one setting). It lowers the gain at the strong end (54 dB at -10) and sits at the
  maximum 73 dB from -30 down, so at the weak end it behaves like manual 71.
- **Sporadic errors at good SNR.** Single gross frames at -20, -30 and -40 dB appear in otherwise
  clean points and do not follow the level. They match the occasional bad frames seen in earlier
  runs (#66) and are not a sensitivity effect.

## Limits

- Only relative levels. The absolute input power at board B is unknown until the S21 of the path
  is measured (#29), so the threshold is not given in dBm.
- Each point is one run of 100 frames (25,600 payload bits at most): a BER of 0 means below about
  4e-5, and differences of a few frames between neighbouring points are within the scatter.
- Board A replays the frame cyclically: each attempt on B starts on a continuous signal, so this
  is not a packet-mode (burst) sensitivity.
- One carrier (915 MHz), one board pair, one temperature (board B Zynq 68.5 C at the end).
