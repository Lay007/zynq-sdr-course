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

## Messages sent once, from the board consoles

`zmsg` (Lab 11.46) got the same burst format and the listen mode: `zmsg send --once` builds
silence, the 32-symbol lead-in, the reference symbol and one packet-v1 frame, and transmits it one
time; `zmsg receive --listen` re-arms the listening receiver until messages arrive. Getting there
took four fixes in the tool, each found on the bench:

1. **The one-shot buffer was cut short.** A plain (non-cyclic) `iio_writedev` queues its buffer and
   closes it at once, and the close stops the DMA. Board A recorded its own transmission through
   the splitter: only about 1000 samples went out, and the decoded frames had about 50 % errors from
   payload bit ~120 on. The message buffer is now followed by 16 buffers of zeros; the kernel has 4
   blocks, so queueing them waits until the message has gone out. Twelve recorded transmissions
   were then all 1470-1480 samples long, as computed.
2. **A click before every message.** Rewriting the TX settings (sample rate, LO, gain) retunes the
   chip even when nothing changes. Board A's own recording showed a 34-sample click, three times
   stronger than the message, about 65 ms before it; a listening receiver takes it for a packet.
   The settings are now written only when they differ.
3. **Lost start pulses.** The tool wrote the start bit high and low with two back-to-back `mmap`
   writes. The bridge samples `gp_ctrl` through a two-flop synchronizer in the modem's clock
   domain, and about one start in seven was missed (status `0x810`: idle, neither done nor
   timeout). Worse, the tool then took the old symbol count as a fresh frame and printed the
   previous message again. Start and clear are now held for 20 µs, and only the done bit counts as
   a reception. (`devmem` is slow enough never to hit this. The earlier cyclic `zmsg` campaign was
   re-measured: 199 of 200 instead of 200 of 200, see
   [two-board-message-20261014.md](two-board-message-20261014.md).)
4. **The old message came back.** After a cyclic `iio_writedev` was killed with `kill -9`, board A's
   DAC kept playing its buffer, silent only while the TX LO was off. The next `send --once` turned
   the LO on and the listening receiver decoded the old message: in a reproduction, all 10
   "deliveries" were the stale one. Transmitters are now stopped with SIGTERM first, `zmsg stop`
   drains the DAC with a short cyclic zero buffer, and `quiet_board` in the Python tools tries a
   plain `kill` before `kill -9`.

Results with the final tool (md5 `94431cd8`), one message every 0.9 s on average, board B at
manual 71 dB (`two_board_zmsg_once.py`, raw data
[`zmsg-once-20261015.json`](zmsg-once-20261015.json)):

| receiver | TX | sent | delivered | wrong message accepted | duplicates |
|---|---:|---:|---:|---:|---:|
| listen | -30 dB | 500 | **494 (98.8 %)** | 0 | 0 |
| listen | -50 dB | 200 | 159 (79.5 %) | 0 | 0 |
| fixed window | -30 dB | 100 | 6 | 0 | 0 |

The receiver also locked on frames whose CRC failed: 54 of 548 locks at -30 dB in listen mode, and
49 of 55 in the fixed window, where 20 213 short attempts let the frame sync see noise every time
(about 16.5 million bits; at the 6e-6 per bit of a random 24-bit match this gives a few tens of
false locks, the observed order). The CRC rejected all of them. The listen-mode failures are
false locks on noise too: with board A sending nothing, board B listening for 300 s locked 33 times
with its TX LO off and 21 times with the LO on, every time with a failed CRC. That is 0.07-0.11 per
second, the rate of the campaign (54 in about 490 s of listening). At the per-bit probability of a
random match, it means the packet detector lets noise through to the frame sync for roughly 1-2 %
of the time; each such lock costs the receiver a few milliseconds, too little to explain the lost
messages. At
-50 dB about 20 % of the messages were lost, more than the 11-13 % of frames that were not clean
in the sensitivity sweep at the same level. The cause of the difference was not investigated.

## Limits

- **Listen mode needs gaps.** The detector's noise estimate is a long average. At gap 1 (signal
  half of the time) it is too high and 18-59 of 100 frames came out gross; a continuous stream
  in listen mode mostly does not lock at all. Gap 4 (signal 20 % of the time) and longer work.
  For a continuous stream keep listen mode off, as all earlier labs do.
- The first reception after a reset or an image load can fail while the noise estimate settles.
- The board results are for one board pair, one carrier, conducted, at about 70 C on board B; one
  run per point except steps H and L.
- The lead-in exists in the host tools (`two_board_burst.burst_iq`, `two_board_message.once_iq`) and
  in `zmsg send --once`; the fabric transmitter does not use it.
