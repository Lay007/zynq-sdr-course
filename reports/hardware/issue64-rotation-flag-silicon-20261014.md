# Rotation flag (#64) and the inverted-decision fix on silicon, 2026-10-14

Image: `zynq-sdr-course-artifacts/bitstreams/issue64-rotation-flag-decision-fix` (sha256 `95c5f010...`,
source commit `a8be74a`), written to board B's SD card and cold-booted. Raw results:
[`issue64-rotation-flag-silicon-20261014.json`](issue64-rotation-flag-silicon-20261014.json).

## PL fabric loopback (no RF), 40 bursts each

| Case | Full frames | Bit errors | `gp_status[6:5]` |
|---|---:|---:|---|
| BPSK, decision mode 00 (I) | 40/40 | 0 | 0 in all 40 |
| BPSK, decision mode 01 (-I) | 40/40 | 0 | 2 (180 degrees) in all 40 |
| QPSK | 40/40 | 0 | 0 in all 40 |

On the previous image (`69023a2b`) decision mode 01 locked 0 of 20 bursts at any start offset:
`-sym_i` overflowed at -32768. The `~sym_i` fix (commit `a8be74a`) is confirmed, and the
inverted lock is now reported.

## Two-board link (board A TX1 -> 50 dB path -> board B RX1, 915 MHz, TX -10 dB, RX 50 dB), 200 frames each

| Mode | Lost | Clean | Payload bit errors | Rotation of the clean frames |
|---|---:|---:|---:|---|
| Absolute QPSK | 18 | 160 | 2591 / 46592 | 0: 38, 1: 46, 2: 43, 3: 33 |
| Differential QPSK | 19 | 180 | 2 / 46336 | 0: 180 |

In absolute mode the Costas loop lands in any of the four quadrants and the counter resolves all of
them; the flag now shows which one, about evenly spread. The payload errors come from the roughly
20 non-clean frames, the known whole-burst false locks of absolute mode (Lab 11.42). In
differential mode the rotation is removed before the counter, so the flag reads 0.
