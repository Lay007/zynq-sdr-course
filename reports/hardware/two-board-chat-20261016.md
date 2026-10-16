# Two-board chat through the mailboxes (#67, #69), 2026-10-16

Both boards ran the course image with the Lab 5.12 mailbox (`MODE = 1`, Lab 11.49) and `zmbox chat`:
every line typed on one board goes out with TX_START, and the other board, which listens all the
time (RX_LISTEN), prints it. The first chat delivered 7 of 10 lines in each direction. Getting it
to work took one RTL fix (#69), two fixes in `zmbox`, and the silicon check of the DAC FIFO fix
(#67). This report covers all four, in the order they were found. Raw data:
[`two-board-chat-20261016.json`](two-board-chat-20261016.json).

Bench: board A TX1 -> variable attenuator (30 dB) -> splitter -> {50 ohm, board B RX1, RTL-SDR};
board B TX1 -> 30 dB -> board A RX1. 915 MHz, RX manual 71 dB on both boards. Images:
`issue67-chat-dac-cadence` (md5 `0b5b0762`, source 1c15ae6) at first, then
`issue69-listen-silent` (md5 `2f5cc35d`, source 5b61094) on both boards.

## The DAC between bursts (#67)

With no vendor DMA stream, the old DAC FIFO mux wrote the FIFO only during a burst, and between
bursts the DAC held the last word: a carrier at the LO. The fix writes on the FIFO's own read
request, so the FIFO gets zeros when there is nothing to send. Board B sent three fabric bursts
with no DMA stream at all (`ZMBOX_NO_ZERO_STREAM=1`, no `iio_writedev` running) and kept its TX
on for a second; board A recorded its RX. Level in the gaps, against the noise after the TX LO
was switched off:

| image | DMA zero stream | gaps |
|---|---|---:|
| before the fix (md5 `4fc4aa80`) | none | +40.3 dB, as strong as the burst |
| with the fix | none | +9.8 dB |
| with the fix | running | +9.8 dB |

Most of the remaining 9.8 dB (89 %) is one line 0.3 kHz from the LO: the TX LO leakage,
offset by the difference between the two boards' references. The zero stream is no longer needed.

## A message that came out half as long

Board A's one-shot `zmsg send --once`, delivered 494 of 500 on Lab 11.48, now reached nobody
(0 of 20). Board B recorded it: 883 samples instead of about 1766, and a cyclic `zmsg` stream that
repeated every 608 samples, half a frame. The new mux was the obvious suspect. A simulation of the
real ADI blocks (`util_upack2`, `util_rfifo`) with both mux versions showed the same FIFO writes for
every clock ratio, and booting the old image settled it: right after boot the old image sent the
stream correctly, and after one run of `zmbox` it showed the same halving.

`zmbox` set all four DAC channels to the DMA source. In `axi_ad9361` a channel's enable towards the
unpacker is exactly "source is DMA", so the unpacker then took `zmsg`'s two-channel buffer for a
four-channel one, and TX1 played every second sample. `zmbox` now sets only TX1 (I0, Q0) to DMA and
TX2 to zero; the cyclic stream again repeats every frame (1216 samples).

## A strong signal right before every burst

Board A sending with the fabric modem (`zmbox send`, one call per message) reached board B 6 times
out of 40; the same messages from the DMA (`zmsg send --once`) arrived 40 of 40. `zmbox` wrote the
sample rate and the LO on every call. Rewriting them retunes the chip even when nothing changes,
and the TX calibration that follows put about 30 ms of a signal 41 dB over the noise on the air,
just before the burst. The listening receiver took that for the packet. This is the mistake
already found and fixed in `zmsg` for Lab 11.48, not carried over to `zmbox`. With settings written
only when they differ: 40 of 40.

## A listening board that transmits (#69)

With both fixes the chat still lost a third of the lines, and none of the lost ones reached the
CRC: the receiver did not lock on them at all. Board B recorded board A's chat while six lines were
typed and found seventeen bursts. Every 138 ms, at each re-armed 136 ms listening attempt, the
listening board transmitted a 1344-sample burst: the ROM frame of the BER labs (168 symbols, no
lead-in). A listening attempt starts the core through the same edge as a transmission, and the
QPSK transmitter played its frame each time. That frame collides with the other board's message
and, through the board's own TX->RX leakage, occupies the attempt it was listening with.

Earlier results did not show this because the listening board had its TX LO off: 498 of 500 on
Lab 11.49 and 5000 of 5000 on one board.

The fix keeps the DAC-facing stream silent during a listening attempt (the fabric loopback still
sees the modem). `tb_message_modem_listen` now also counts what the listening copy sends: 2764
samples before the fix, 0 after. The first build with the fix missed timing on an unrelated path,
the phase picker (matched filter output -> |I|+|Q| -> threshold -> accumulator controls, ten logic
levels, -1.119 ns); placement variants did not close it. The picker got one input register stage,
which delays the stream by a clock and changes nothing else (Block 5 HDL smoke 46/46, same
results). The kept image met timing with the ExtraNetDelay_high variant: WNS +0.008 ns, TNS 0,
WHS +0.041 ns.

On silicon, board B listening in chat with its TX on puts nothing on the air apart from the
calibration when the LO comes on, and board A's messages to it arrive 30 of 30 (12 of 20 on the
old image).

## The chat, both boards on the new image

| B TX | rounds | A -> B | B -> A |
|---:|---:|---:|---:|
| -20 dB | 30 | 29 | 24 |
| -30 dB | 30 | 30 | 25 |
| -40 dB | 30 | 30 | 28 |
| -50 dB | 50 | 47 | 45 |

Board A at TX -30 dB throughout. No line arrived corrupted or twice, and no packet failed the CRC.
For comparison, the image before #69 gave 20-28 of 30 per direction.

B -> A improves as board B gets quieter. The B -> A path has no splitter and is the stronger one.
With board A only listening (TX off), board B's messages arrived 35 of 40 at -30 dB and 40 of 40
at -50 dB, so at -20...-30 dB board A's receiver at 71 dB is overdriven. That is a property of
the bench, not of the chat.

What is left at the quiet setting, 3 of 50 and 5 of 50, is not explained. All lost lines failed
before frame lock. A board's own transmission does not cause it: with board B typing a line every
3 s and board A's message 1.5 s later, 39 of 40 arrived, and 39 of 40 with board B silent.

## Limits

- One board pair, one carrier, conducted, one run per point; at 30-50 rounds a single loss is
  2-3 %.
- The overdrive explanation for B -> A at -20...-30 dB rests on the one-way runs above; the RX
  level was not measured.
- Board A's SD card was full. To make room, two LoRa-project images with verified byte-identical
  copies (one in the artifacts repository, one in `7020/backups`) were deleted from it; the LoRa
  image used before the chat is still on the card as `system_top.bit.lora_before_chat_20261016`.
