# AD9361 two-board gain and overload grid — 2026-10-13

## Result

The modem's own signal was sent from board A to board B through a conducted path, and board B's
receive gain and board A's transmit gain were swept on an 8 x 6 grid at 915 MHz. For every point
board B reported its RSSI, a raw ADC capture (peak, RMS, clipped fraction) and 30 on-chip BER
frames. With the variable attenuator at 0 dB the strongest settings drive board B's 12-bit ADC into
clipping, so this run records the **large-signal boundary** that the 2026-07-15 table
([`ad9361-gain-overload-table-20260715.md`](ad9361-gain-overload-table-20260715.md)) left open, and
the low-signal edge on the same grid.

All levels are relative. The passive path has not been calibrated (S21), so no row is an absolute
input power.

## Setup

| Parameter | Value |
|---|---|
| RF chain | A TX1 -> variable attenuator **0 dB** -> 30 dB fixed attenuator -> 3-way splitter -> B RX1 / RTL-SDR / 50 ohm |
| Boards | A: vendor image with the DDS/DMA core (continuous `iio_writedev` TX); B: course image, md5 `31f118ac` (differential QPSK) |
| Carrier | 915 MHz, both LOs from the boards' own references (real inter-board CFO) |
| Sample rate / RF bandwidth | 3.84 MS/s / 18 MHz on both boards |
| Signal | Lab 11.45 frame: differential QPSK, RRC, 8 samples per symbol, 24-symbol preamble, 256-bit payload, repeated continuously |
| Receiver mode | `gp_ctrl` `0x3f630`: raw RX, DC blocker, Costas, phase picker, payload-position telemetry, Gardner, differential decoding |
| Gain mode | manual on board B |
| Per point | RSSI, one 65,536-sample `iio_readdev` capture on board B, 30 BER frames (7680 payload bits when all lock) |
| Reproduce | `python two_board_gain_overload_sweep.py --bench "..." --json-out ...` in `blocks/block_11_integrated_sdr_project/python` |
| Raw data | [`ad9361-two-board-overload-20261013.json`](ad9361-two-board-overload-20261013.json); a first pass with the variable attenuator at 20 dB is in [`ad9361-two-board-overload-20261013-att20.json`](ad9361-two-board-overload-20261013-att20.json) (its ADC-peak field came from a register that is not a peak in this mode; use only its RSSI and BER columns) |

ADC levels are against 2048 per component. The RMS is the complex RMS, so it can exceed 0 dBFS when
both rails clip.

## Where clipping starts

| RX gain, dB | Last TX gain without clipping | First TX gain with clipping |
|---:|---|---|
| 71 | -30 dB (peak -9.5 dBFS) | -20 dB (0.15 %); -10 dB clips 53 % of samples |
| 60 | -10 dB (peak -0.1 dBFS) | -5 dB (15 %) |
| 50 | -5 dB (peak -1.8 dBFS) | 0 dB (5.6 %) |
| 40 and below | 0 dB, the top of the TX range | none reached |

## Full grid

| RX gain, dB | TX gain, dB | RSSI | ADC peak, dBFS | ADC RMS, dBFS | Clipped, % | Locked | Clean | Payload bit errors |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 71 | -40 | 103.25 | -18.4 | -23.2 | 0.00 | 30/30 | 29 | 2/7680 |
| 71 | -30 | 93.50 | -9.5 | -13.4 | 0.00 | 30/30 | 30 | 0/7680 |
| 71 | -20 | 83.00 | 0.0 | -3.3 | 0.15 | 28/30 | 28 | 0/7168 |
| 71 | -10 | 80.00 | 0.0 | 1.7 | 52.87 | 27/30 | 25 | 10/6912 |
| 71 | -5 | 80.00 | 0.0 | 2.1 | 28.41 | 26/30 | 22 | 16/6656 |
| 71 | 0 | 80.00 | 0.0 | 2.5 | 60.64 | 25/30 | 20 | 24/6400 |
| 60 | -40 | 102.75 | -28.1 | -33.8 | 0.00 | 30/30 | 26 | 30/7680 |
| 60 | -30 | 92.75 | -19.5 | -24.0 | 0.00 | 29/30 | 25 | 22/7424 |
| 60 | -20 | 82.75 | -9.8 | -13.9 | 0.00 | 30/30 | 28 | 6/7680 |
| 60 | -10 | 73.25 | -0.1 | -4.0 | 0.00 | 26/30 | 26 | 0/6656 |
| 60 | -5 | 69.25 | 0.0 | -0.4 | 14.66 | 25/30 | 25 | 0/6400 |
| 60 | 0 | 69.00 | 0.0 | 1.4 | 50.52 | 26/30 | 21 | 20/6656 |
| 50 | -40 | 100.50 | -32.8 | -39.7 | 0.00 | 24/30 | 20 | 45/6144 |
| 50 | -30 | 91.25 | -25.3 | -30.5 | 0.00 | 29/30 | 24 | 16/7424 |
| 50 | -20 | 81.25 | -16.3 | -20.5 | 0.00 | 29/30 | 28 | 6/7424 |
| 50 | -10 | 71.75 | -6.7 | -10.7 | 0.00 | 28/30 | 27 | 10/7168 |
| 50 | -5 | 66.75 | -1.8 | -5.8 | 0.00 | 27/30 | 27 | 0/6912 |
| 50 | 0 | 62.25 | 0.0 | -1.1 | 5.62 | 30/30 | 27 | 16/7680 |
| 40 | -40 | 94.25 | -35.9 | -45.5 | 0.00 | 23/30 | 15 | 55/5888 |
| 40 | -30 | 90.50 | -32.4 | -39.6 | 0.00 | 24/30 | 22 | 40/6144 |
| 40 | -20 | 81.00 | -25.5 | -30.3 | 0.00 | 27/30 | 26 | 2/6912 |
| 40 | -10 | 71.50 | -16.4 | -20.5 | 0.00 | 29/30 | 28 | 2/7424 |
| 40 | -5 | 66.75 | -11.6 | -15.7 | 0.00 | 30/30 | 29 | 4/7680 |
| 40 | 0 | 61.75 | -6.8 | -10.8 | 0.00 | 25/30 | 25 | 0/6400 |
| 30 | -40 | 86.00 | -35.6 | -46.6 | 0.00 | 14/30 | 1 | 289/3584 |
| 30 | -30 | 84.50 | -35.4 | -43.6 | 0.00 | 23/30 | 15 | 63/5888 |
| 30 | -20 | 77.50 | -29.7 | -35.8 | 0.00 | 22/30 | 20 | 12/5632 |
| 30 | -10 | 68.25 | -21.9 | -26.2 | 0.00 | 25/30 | 21 | 12/6400 |
| 30 | -5 | 63.25 | -17.4 | -21.4 | 0.00 | 27/30 | 25 | 6/6912 |
| 30 | 0 | 58.50 | -12.6 | -16.5 | 0.00 | 29/30 | 26 | 8/7424 |
| 20 | -40 | 74.00 | -37.6 | -47.0 | 0.00 | 1/30 | 0 | 42/256 |
| 20 | -30 | 74.00 | -37.3 | -46.6 | 0.00 | 14/30 | 1 | 233/3584 |
| 20 | -20 | 72.50 | -34.9 | -43.5 | 0.00 | 25/30 | 18 | 122/6400 |
| 20 | -10 | 65.75 | -29.8 | -35.9 | 0.00 | 24/30 | 21 | 10/6144 |
| 20 | -5 | 61.25 | -26.3 | -31.3 | 0.00 | 29/30 | 22 | 16/7424 |
| 20 | 0 | 56.25 | -22.1 | -26.4 | 0.00 | 28/30 | 25 | 20/7168 |
| 10 | -40 | 64.00 | -38.6 | -47.2 | 0.00 | 0/30 | 0 | 0/0 |
| 10 | -30 | 64.00 | -38.3 | -47.1 | 0.00 | 2/30 | 0 | 37/512 |
| 10 | -20 | 64.00 | -37.3 | -46.5 | 0.00 | 15/30 | 3 | 162/3840 |
| 10 | -10 | 62.50 | -34.9 | -43.1 | 0.00 | 19/30 | 13 | 97/4864 |
| 10 | -5 | 59.50 | -32.4 | -39.6 | 0.00 | 24/30 | 18 | 27/6144 |
| 10 | 0 | 55.25 | -28.5 | -35.3 | 0.00 | 25/30 | 21 | 8/6400 |
| 0 | -40 | 51.00 | -37.9 | -47.0 | 0.00 | 0/30 | 0 | 0/0 |
| 0 | -30 | 51.00 | -38.3 | -47.0 | 0.00 | 0/30 | 0 | 0/0 |
| 0 | -20 | 51.00 | -37.3 | -46.9 | 0.00 | 0/30 | 0 | 0/0 |
| 0 | -10 | 51.00 | -37.6 | -46.4 | 0.00 | 15/30 | 1 | 200/3840 |
| 0 | -5 | 50.25 | -35.6 | -45.3 | 0.00 | 23/30 | 10 | 202/5888 |
| 0 | 0 | 49.50 | -34.4 | -43.1 | 0.00 | 24/30 | 17 | 59/6144 |

## What the grid says

- **QPSK survives hard clipping better than expected.** At RX 71 dB and TX 0 dB, 61 % of the
  samples sit on a rail, and the link still decodes 25 of 30 frames with 24 errors in 6400 bits
  (3.7e-3). The decision is a sign, which clipping preserves. What clipping does cost is visible
  too: the errors at those points are higher than one step lower, where the same rows are clean.
- **The RSSI stops being a level meter in overload.** At RX 71 dB it reads 80.00 dB at TX -10, -5
  and 0 dB, while the input grows by 10 dB (the RTL-SDR on the third splitter port shows that
  growth: -39.2, -35.3, -30.8 dBFS). A gain loop driven by RSSI alone would not see how far it is
  in overload; this is the motivation for the AGC experiment of issue #58.
- **The low edge is noise, and lower gain moves it up.** With nothing transmitted, the ADC RMS is
  about -47 dBFS at low RX gain. Below about -40 dBFS RMS the frame sync starts to miss and the
  BER climbs. The same TX -20 dB gives 0/7680 at RX 71 dB, 2/6912 at 40 dB, 122/6400 at 20 dB and
  no lock at 0 dB: less RX gain means less of the front-end gain ahead of the noise that the later
  stages add.
- **Working window.** Points with an ADC peak between about -20 and -2 dBFS decode with at most a
  few errors per 7680 bits; for example RX 60 dB / TX -10 dB, RX 50 dB / TX -5 dB and RX 40 dB /
  TX 0 dB gave 0 errors. Thirty frames per point resolve a BER of about 1.3e-4; zero errors means
  below 3.9e-4 at 95 % confidence, not zero.
- **Cross-check of the variable attenuator.** The 20 dB pass and this 0 dB pass agree at
  equivalent points: RSSI 105.25 dB (20 dB setting, TX -20) against 103.25 dB (0 dB setting,
  TX -40), so the "20 dB" setting is about 18-20 dB at 915 MHz.

## Limits and remaining work

1. Calibrate the passive path (cable, attenuators, splitter) with a NanoVNA at 915 MHz and convert
   the table to input power in dBm. The path is lossier than its nominal 30 dB plus an ideal
   splitter by roughly 7-12 dB (estimated from the RSSI against the 2026-07-20 run).
2. Repeat at one lower and one higher frequency inside the splitter's and the RTL-SDR's range.
3. More frames at the boundary points to resolve the clipping penalty below 1e-3.
