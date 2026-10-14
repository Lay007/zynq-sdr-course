# Two-board packet mode: a frame after silence, 2026-10-14

Bench: board A TX1 -> 30 dB -> 3-way splitter -> board B RX1, conducted, 915 MHz. Board A replays
ONE long differential QPSK frame (152 symbols, 317 us) followed by a gap of silence of 0, 1, 4, 19
or 99 frame lengths, cyclically (gap 0 is the continuous stream used by every earlier two-board
lab). Board B (image `3d492301`, mode `0x2D630`) arms the receiver 100 times per point at a random
moment relative to the bursts. TX -30, -10 and -50 dB; board B at manual 71 dB or slow-attack AGC.
Script: `blocks/block_11_integrated_sdr_project/python/two_board_burst.py`. Raw data:
[`two-board-burst-20261014.json`](two-board-burst-20261014.json).

## Result, all six RX/TX settings pooled (600 attempts per gap)

| gap (frames) | share of time with signal | locked | clean | locked / attempts |
|---:|---:|---:|---:|---:|
| 0 | 1 | 592 | 555 | 0.99 |
| 1 | 1/2 | 162 | 147 | 0.27 |
| 4 | 1/5 | 87 | 84 | 0.145 |
| 19 | 1/20 | 14 | 12 | 0.023 |
| 99 | 1/100 | 4 | 4 | 0.007 |

Per-setting rows are in the JSON; the six settings give the same picture.

## What it shows

- **The receiver does not wait for a packet.** The lock rate follows the share of time with
  signal (about 0.5-0.7 of it). An attempt that starts in silence ends without a frame.
- **Why (from the RTL, `qpsk_zynq_ber_top`).** The receive window is fixed when the receiver is
  armed: the symbol sampler emits `symbol_count + RX_SAMPLE_MARGIN` = 152 + 256 = 408 symbols
  (0.85 ms) and stops. The signal-present gate holds the decisions back while there is only noise.
  When the sampler stops, no more symbols arrive and the idle watchdog (`RX_IDLE_TIMEOUT_CYCLES`
  = 4096) ends the attempt. On the board, a failed attempt is already finished at the first status
  read: status `0x81C` (done + timeout), 0 symbols received. This design came from self-OTA, where
  the same core transmits the frame when it is armed, so the frame is known to arrive within the
  margin.
- **A frame that is caught decodes well after silence.** 555 of 592 locked frames are clean in
  the continuous stream; 147/162, 84/87, 12/14 and 4/4 with gaps. The persistent DC estimate
  (#66), the Costas and Gardner loops and the slow-attack AGC (which sits at 71-73 dB during long
  gaps) do not prevent decoding of a burst that follows 0.3-31 ms of silence. With few frames
  caught at long gaps, this is a weak statement (14 and 4 frames).
- **Consequence for the message labs.** Every two-board result so far (Lab 11.45, zmsg of
  Lab 11.46, the sensitivity sweep) relies on board A transmitting continuously, so that any
  receive window contains a frame. Real packet reception, where board A sends a message once,
  needs a "listen" mode in the receiver: the sampler runs until the preamble locks (or until a long,
  software-chosen timeout), instead of a fixed 408-symbol window.

## Limits

- One run per point; 100 attempts each.
- The arming moment relative to the bursts is random but not measured, so the effective window
  length is inferred from the rates and the RTL, not measured directly.
