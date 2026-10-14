# DC blocker kept across frames (#66) on silicon, 2026-10-14

Follow-up to [`dc-blocker-level-step-20261014.md`](dc-blocker-level-step-20261014.md). The QPSK
receiver's DC blocker used to restart its running mean at every frame start. At the preamble it
then averaged only a few hundred samples, many of them the repeated differential preamble symbol,
so it subtracted part of the preamble, and after a sudden 20 dB level drop the offset it had
learned was most of the weak signal.

Change (commit `0220cfe`): `qpsk_zynq_ber_top` keeps the estimate across frames (`DC_PERSIST = 1`)
with a time constant of 2^13 samples. The receiver gets samples only during a burst, so between
bursts the estimate holds. `dc_blocker.v` itself is unchanged; the chain has a separate `rst_dc`
input, and benches that drive the chain directly tie it to their `rst` and run bit for bit as
before.

Image: `zynq-sdr-course-artifacts/bitstreams/issue66-dc-blocker-persist` (sha256 `3d492301...`).
The full build missed timing by -0.233 ns on the known coarse-CFO DSP path, so the image is the
same place/route variant as for #65: WNS +0.025 ns, WHS +0.021 ns, 81100 nets routed. It was
written to board B's SD card and loaded by a warm reboot (AD9361 calibrated without errors). Raw
results: [`dc-blocker-persist-silicon-20261014.json`](dc-blocker-persist-silicon-20261014.json).
Board B, which has no fan, stayed at 67.9-69.9 °C (Zynq XADC) throughout.

## Simulation before the build

`tools/run_qpsk_dc_bursts_sim.py` runs `tb_qpsk_dc_bursts.v`: 80 receptions started at arbitrary
points of one continuous stream, with no reset in between, as on the bench. CFO 500 Hz. Columns:
locked / clean / payload bit errors.

| Stream | kept across frames | reset every frame (before) | DC blocker off |
|---|---|---|---|
| steady level | 62 / 62 / 0 | 53 / 49 / 16 | 62 / 61 / 3 |
| 20 dB drop at symbol 60 every 8 frames | 62 / 59 / 21 (1 gross) | 46 / 29 / 300 (6 gross) | 60 / 59 / 3 |

A restart of the mean on a detected level drop was also tried. It fixed a single reception that
starts from reset, but with the estimate kept across frames it lowered the lock count from 62 to 56,
because the restarted short window learns the next preamble again. It was dropped.

## Regression on silicon

- PL fabric loopback: BPSK modes 00 and 01 and QPSK, 40/40 clean each, with the expected rotation
  flags. The BPSK start-offset sweep is identical to the #65 image.
- Two-board link (915 MHz, TX -10 dB, RX 50 dB, DC blocker on), 200 frames each:

| Mode | #65 image (morning): lost / clean / payload bit errors | this image |
|---|---|---|
| differential | 15 / 181 / 18 | **0 / 200 / 0** |
| absolute | 23 / 150 / 3119 | 4 / 191 / 699 |

## DC blocker on and off, 300 frames each

Lab 11.45 mode, manual RX gain 50 dB. Columns: locked / clean / gross / payload bit errors. The
last column is the same measurement on the #65 image, earlier the same day
([report](dc-blocker-level-step-20261014.md)).

| | this image, DC on | this image, DC off | #65 image, DC on |
|---|---|---|---|
| high level | 300 / 299 / 1 / 101 | 300 / 299 / 0 / 1 | 284 / 278 / 0 / 21 |
| low level (-20 dB) | 299 / 294 / 2 / 38 | 300 / 298 / 0 / 11 | 283 / 259 / 7 / 318 |
| triangle (slow 20 dB ramps) | 300 / 291 / 2 / 159 | 300 / 296 / 1 / 37 | 287 / 267 / 3 / 107 |
| 20 dB drop at symbol 60, every 8 frames | 298 / 279 / **7** / 172 | 299 / 294 / 2 / 35 | 279 / 231 / **35** / 1157 |

## Conclusions

- Measured:
  - With the DC blocker on, almost every frame now locks (about 94 % before);
  - a 20 dB drop mid-frame costs 7 gross frames out of 298 instead of 35;
  - on the two-board link the differential mode decoded 200 of 200 frames clean.
- Measured, and not hidden: on this conducted two-board bench the receiver is still a little better
  with the DC blocker off (drop: 2 gross instead of 7; fewer single-bit errors). The kept estimate
  still holds a few percent of the signal's own mean.
- Single-board self-OTA: measured later the same day, see below.

## Single board: board B's own burst through the cable

Recabled: B TX1 -> variable attenuator (0 dB) -> 30 dB -> splitter -> B RX1, board A off. TX and
RX LOs both at 915 MHz (no CFO), TX 0 dB, RX 60 dB manual. Board B's device tree has no DAC driver,
so the DAC channels were put on the DMA input by `devmem` (`0x79024418` etc. = 2), where the
bridge muxes in the modem burst; with the default DDS source nothing was transmitted.

What makes this case hard: board B emits a continuous carrier at its LO. On the RTL-SDR's
time-averaged spectrum it is about 20 dB above the modem signal, but the bursts occupy only about
3 % of the time there. Board A, connected to the free splitter output afterwards, measured it
properly: during a burst the carrier is 3 dB below the burst (780 against 1103 counts RMS), and it
stays on between bursts. At B's own receiver this carrier is a DC component as strong as the
signal.
The link is marginal (the burst only locks from about 60 dB of RX gain), which is why the clean
counts are low in every column. 100 frames each, locked / clean / gross:

| | #65 image (DC reset every frame) | this image (DC kept) |
|---|---|---|
| DC blocker on | **0 / 0 / 0** | 24 / 4 / 14 |
| DC blocker off | 62 / 32 / 15 | 53 / 40 / 9 |

- With the old per-frame reset, the DC blocker made the single-board link fail completely; with the
  kept estimate a quarter of the frames lock.
- Even here, with a DC about as strong as the signal, the receiver does better with the DC blocker
  off. The AD9361's own DC correction seems to remove the carrier before the samples reach the
  fabric. Assumed, not checked: the July self-OTA result that motivated the blocker came from a
  different board and setup.
- One session, one board, marginal SNR; the DC-off columns of the two images (62 and 53 locked)
  differ by about the run-to-run spread.
