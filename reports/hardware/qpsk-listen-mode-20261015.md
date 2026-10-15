# QPSK receiver listen mode on two boards (#68), 2026-10-14/15

Follow-up of [two-board-burst-20261014.md](two-board-burst-20261014.md): the Lab 11.45 receiver
caught a packet only if one arrived within its fixed 408-symbol window after arming, so every
two-board result needed board A to transmit continuously. This report covers the receiver change,
the simulation, the image and the bench results.

Bench: board A TX1 -> 30 dB -> 3-way splitter -> board B RX1, conducted, 915 MHz. From step I on,
the RTL-SDR was connected again to the third splitter output (before that, the output was open).
Board B: image `issue68-qpsk-listen-mode` (sha256 `3406e253...`, source commit `d634e5d`), mode
`0x2D630`, plus `gp_ctrl[18]` for listen mode. Board A replays one 152-symbol frame followed by
silence (the gap, in frame lengths), cyclically; board B arms the receiver at random moments.
Scripts: `two_board_burst.py`, `two_board_burst_errors.py` (per-frame error positions),
`tools/run_qpsk_listen_sim.py`. Raw data:
[`qpsk-listen-mode-20261015.json`](qpsk-listen-mode-20261015.json).

## What changed in the receiver (`gp_ctrl[18]` = 1; 0 keeps every lab bit-identical)

- **Window.** The symbol sampler runs for the whole 16-bit counter (65535 symbols, 136 ms) instead
  of frame + 256 symbols. The idle watchdog watches the sampler, so an attempt with no packet still
  ends by itself, with the timeout bit.
- **Packet detector** (`qpsk_packet_detect.v`). It compares a short mean of the symbol `|I|+|Q|`
  (about 8 symbols) with a long one (about 4096 symbols, the noise level) and reports a packet
  when the short mean is 1.5 times the long one. The noise estimate is kept across receptions.
  The old fixed gate (`|I|+|Q| >= 8`) does not work at 71 dB: board B's noise alone is 16 counts
  rms at the ADC and keeps it open.
- **Loops held in silence.** While no packet is present, the Gardner timing loop and the Costas
  loop do not update. Without that, both random-walk on the noise (in simulation the Costas
  frequency wandered by about +-2 kHz and the Gardner step by 1-2 %).
- **Frame sync fed only during packets.** Decisions reach the frame-sync correlator only while a
  packet is present (16-symbol delay so the first symbols are not lost, 64-symbol hang). Over a
  long wait the correlator would otherwise test tens of thousands of noise positions.

Build: default directives, WNS +0.046 ns, WHS +0.031 ns, 81400/81400 nets routed, 36232 LUT
(+204 against the #66 image), DSPs unchanged. Block 5 HDL smoke: 43/43 with the change.

## What changed in the burst format (transmitter only)

Two findings on the way, both about how a differential QPSK burst must start after silence:

1. **Reference symbol.** A differential receiver decodes each symbol against the previous one.
   After silence that one is noise, so the first frame symbol decodes wrong in about 3 cases of 4,
   and the frame sync (23 of the first 24 bits) misses the frame. One symbol with phase state 0
   (the encoder's starting state) in front of the frame fixes that.
2. **Training lead-in.** Even with the reference, about 4 % of frames came out gross (step E).
   The per-frame error positions showed errors from the first payload bits on, and simulation with
   a random symbol timing phase reproduced them: after silence the loops need some symbols to
   settle, and that happened on the preamble the frame sync depends on. A larger Gardner gain for
   the first 32 symbols did not help in simulation (11/30 gross against 8/30) and was not kept.
   32 training symbols (alternating phase states 2 and 0) before the reference fixed it.

## Results on the board

### Lock rate and clean frames, TX -30 dB (100 attempts per point)

| gap (frames) | fixed window, reference | listen, reference | listen, lead 32 |
|---:|---:|---:|---:|
| 1 | 41-49 locked | 100 locked, 67 clean | 100 locked, 52-58 clean |
| 4 | 18-20 locked | 100 / 97-99 clean | **100 / 100 clean** |
| 19 | 4-8 locked | 100 / 94-97 clean | **100 / 100 clean** |
| 99 | 1 locked | 97-98 / 92-94 clean | **100 / 100 clean** |

Both RX settings (manual 71 dB and slow-attack AGC) give the same picture; the per-setting rows
and the TX -10 and -50 dB points are in the JSON. At TX -10 dB, manual 71 dB overloads the input
(as in the continuous sensitivity sweep) and at -50 dB the link is near its threshold, so those
points have 78-98 clean frames in every mode.

### Long run, gap 19, TX -30 dB, manual 71 dB, 10 000 attempts each

| | locked | clean | gross (> 8 of 256 bits) |
|---|---:|---:|---:|
| fixed window, continuous stream (the old way, step F) | 9998 | 9952 | 32 (0.32 %) |
| listen, reference only (step E) | 10000 | 9510 | 435 (4.35 %) |
| **listen, lead 32 (step L)** | **10000** | **9986** | **9 (0.09 %)** |

A separate 1000-attempt run with lead 32 (step H): 1000 locked, 1000 clean.

### Sensitivity, listen, lead 32, gap 19 (clean frames of 100)

| TX dB | -10 | -15 | -20 ... -40 | -45 | -50 | -55 | -60 | -65 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| manual 71 dB | 80 | 99 | 100 | 95 | 87 | 33 | 0 | 0 |
| slow-attack AGC | 82 | 92 | 100 | 98 | 89 | 53 | 0 | 0 |

The threshold is where it is for the continuous stream
([two-board-sensitivity-20261014.md](two-board-sensitivity-20261014.md): 94 clean at -50, about
40 at -55): listening for packets costs no sensitivity.

### Simulation (the same receiver, board-like noise, random timing phase)

| case | receptions | clean | gross |
|---|---:|---:|---:|
| gap 19, fixed window | 20 | 0 (all timed out) | 0 |
| gap 4, listen, reference only | 30 | 22 | 8 |
| gap 4, listen, lead 32 | 30 | 29 | 1 (first reception after reset) |
| gap 19, listen, lead 32 | 20 | 20 | 0 |
| gap 99, listen, lead 32 | 10 | 9 | 1 |
| gap 19, weak (TX -50 level), listen, lead 32 | 20 | 20 | 0 |
| noise only, listen | 1 | 0 | 0 (ended by timeout after the 65535-symbol window) |

## Limits

- **Listen mode needs gaps.** The detector's noise estimate is a long average. At gap 1 (signal
  half of the time) it is too high and 18-59 of 100 frames came out gross; a continuous stream
  in listen mode mostly does not lock at all. Gap 4 (signal 20 % of the time) and longer work.
  For a continuous stream keep listen mode off, as all earlier labs do.
- The first reception after a reset or an image load can fail while the noise estimate settles.
- The board results are for one board pair, one carrier, conducted, at about 70 C on board B; one
  run per point except steps H and L.
- The lead-in is a host-side burst format (`two_board_burst.burst_iq`); the fabric transmitter and
  the message tools (Lab 11.46, zmsg) do not use it yet.
