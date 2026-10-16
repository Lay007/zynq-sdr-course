# Lab 11.50 — Two boards chat through their mailboxes

## Idea

Lab 11.49 sent messages one way: board A transmitted, board B's mailbox listened. A chat needs both
directions at once. Each board listens all the time, and whenever someone types a line it stops
listening for a moment, sends the line and goes back to listening. The program is short, because
the mailbox already does the hard part. What makes this lab worth doing is what the first chat
showed: it delivered 7 lines out of 10 in each direction, and all three causes had been there in
the earlier labs without showing. Each was hidden by something the one-way setup happened to do.

## How `zmbox chat` works

```text
start:        set up the radio once (LO, gains, DAC source); RX_LISTEN
loop:         STATUS.RX_VALID?  -> print "<< text" if RX_META says CRC_OK; RX_ACK
              a line on stdin?  -> RX_STOP
                                   write TX_SEQUENCE, TX_LENGTH, TX_DATA
                                   TX_START, repeated until STATUS.TX_BUSY shows it was taken
                                   wait for RX_VALID: our own burst, heard through the board; discard it
                                   print ">> text"; RX_LISTEN
```

Three details come from the mailbox contract of Lab 11.49:

- **TX_START is refused while the mailbox listens**, and RX_STOP does not cut short a listening
  attempt that has already begun (up to 136 ms). So the program repeats TX_START until it is taken.
  It watches TX_BUSY, not TX_DONE: TX_DONE stays set from the previous message.
- **A sending board hears itself.** TX_START sends and receives in the same attempt, so the board's
  own burst comes back through the leakage between TX and RX on the board. The chat throws that one
  away.
- **The name goes into the payload.** Packet-v1 carries at most 27 bytes, so "A: " plus 24
  characters is all one line can hold; longer lines are cut.

## What you need

- Two boards with the image `issue69-listen-silent` from the artifacts repository (sha256
  `b763660c...`). Older mailbox images work for one-way messages but not for a chat; the third
  finding below explains why.
- Two conducted paths, one per direction. On the course bench: board A TX1 -> variable attenuator
  (30 dB) -> splitter -> board B RX1, and board B TX1 -> 30 dB -> board A RX1. 915 MHz, RX gain 71 dB
  on both boards.
- `/root/zmbox` on both boards, built from `blocks/block_11_integrated_sdr_project/sw/zmbox.c`. Both
  boards lose `/root` on a reboot, including the one that loads a new image.

## Without hardware

```bash
python tools/run_block5_hdl_smoke.py --test tb_message_modem_listen
```

Two copies of the bridge wrapper, T and R: T sends two messages, R listens and must deliver both.
Since the third finding below, the testbench also counts the samples R puts on its own DAC stream
while it listens. It must be zero; before the fix it was 2764.

## Running it

Start the chat on both boards, then type on either one. The output below was recorded on the course
bench with the lines fed in by a script, so the typed text itself does not appear; at a terminal you
also see what you type.

```text
board-a$ ./zmbox chat --name A --tx-gain -30
chat as A: type a line (at most 27 bytes with the name) and press Enter; Ctrl-C ends
>> A: hello, B here?
<< B: yes, hearing you, A
>> A: loud and clear
<< B: what carrier?
>> A: 915 MHz, conducted
<< B: nice. signing off
>> A: bye
```

```text
board-b$ ./zmbox chat --name B --tx-gain -50
chat as B: type a line (at most 27 bytes with the name) and press Enter; Ctrl-C ends
<< A: hello, B here?
>> B: yes, hearing you, A
<< A: loud and clear
>> B: what carrier?
<< A: 915 MHz, conducted
>> B: nice. signing off
<< A: bye
```

`>>` is a line this board sent, `<<` a line it received. A line that was typed but never arrived
simply does not show up on the other side: the mailbox drops frames with a wrong CRC, so a lost line
never turns into a wrong one.

The same exchange can run on a schedule from the host and be counted:

```bash
cd blocks/block_11_integrated_sdr_project/python
python two_board_chat.py --rounds 100 --tx-gain-b -50 --json-out chat.json
```

Each round board A types `a<k>` and two seconds later board B types `b<k>`. The script prints, for
each direction, how many lines arrived, how many arrived with a text nobody typed and how many
arrived twice.

## What the first chat found

### A message that came out half as long

Before the chat, board A was still sending with `zmsg send --once` (Lab 11.48). Those messages now
reached nobody, 0 out of 20. The other board recorded one with `iio_readdev`: about 880 samples
instead of about 1766. A cyclic `zmsg` stream repeated every 608 samples, half a frame. The DAC was playing every
second sample.

The obvious suspect was the change just made to the DAC FIFO mux (issue #67, below). A simulation of
the real ADI blocks with both versions of the mux wrote the FIFO identically, so the suspect was
probably innocent, and the old image settled it. Right after boot it sent the stream correctly;
after one run of `zmbox` it halved it too.

`zmbox` had set all four DAC channels to the DMA source. In `axi_ad9361` the signal that enables a
channel towards the unpacker is exactly "this channel's source is DMA". With four enabled channels,
the unpacker read `zmsg`'s two-channel buffer as four channels and gave TX1 every second sample.
`zmbox` now sets only TX1 (I0, Q0) to DMA and TX2 to zero.

**Lesson:** when a new image misbehaves, first run the old image with the same sequence of commands.
Here the command sequence was the cause, not the image.

### A strong signal right before every message

Board A then sent with `zmbox send`, one call per message. Board B received 6 of 40, while the same
messages sent with `zmsg --once` arrived 40 of 40. `zmbox` set the sample rate and the LO on every
call. Writing them retunes the AD9361 even when the value does not change, and its TX calibration put
about 30 ms of a signal 41 dB above the noise on the air just before the burst. The listening
receiver took that for the packet.

`zmsg` had the same mistake and lost it in Lab 11.48. The fix (write a setting only when it
differs) never made it into `zmbox`. With it: 40 of 40.

### A listening board that transmits (issue #69)

With both fixes the chat still lost about a third of the lines, and none of them reached the CRC
check: the receiver never locked. Board B recorded board A's air while six lines were typed and
found seventeen bursts. Every 138 ms the listening board sent a 1344-sample burst. That is 168
symbols, the ROM frame of the BER labs without the lead-in.

A listening attempt starts the modem core through the same edge as a transmission, and the QPSK
transmitter played its frame each time. The frame collides with the other board's message. It also
reaches the board's own receiver through the leakage and takes the attempt the board is listening
with.

Lab 11.49 never showed this: its listening board had the TX LO off, so the frames never left the
chip. The fix keeps the DAC-facing stream silent during a listening attempt. On the board, a
listening board now puts nothing on the air. With both `zmbox` fixes in place and TX -30 dB on
both boards, the chat went from 20 of 30 lines in each direction to 30 and 25 of 30.

### And the check the chat was built for (issue #67)

The DAC FIFO mux of the course image used to write the FIFO only while a burst was going out.
Without a vendor DMA stream, the DAC then held the last sample between bursts: a carrier at the LO.
Since Lab 11.47 a cyclic buffer of zeros covered that. The fix writes the FIFO on the FIFO's own
read request, zeros when there is nothing to send. Board B sent bursts with no DMA stream at all
(`ZMBOX_NO_ZERO_STREAM=1`), and board A measured the gaps. They were 40.3 dB above the noise with the
old image, as strong as the burst, and 9.8 dB with the new one, the same as with the zero stream.
That remainder is the TX LO leakage, one line 0.3 kHz from the LO.

## Results

Both boards on `issue69-listen-silent`, board A at TX -30 dB:

| board B TX | rounds | A -> B | B -> A |
|---:|---:|---:|---:|
| -20 dB | 30 | 29 | 24 |
| -30 dB | 30 | 30 | 25 |
| -40 dB | 30 | 30 | 28 |
| -50 dB | 50 | 47 | 45 |

A longer run at the default levels (board B at -50 dB), 100 rounds: 90 lines from A to B and 85
from B to A. Each piece of the chat on its own loses less. A board that only listens with its TX
off receives 59 of 60; a board that listens in chat with its TX on, 60 of 60; lines sent from
`zmbox chat` to a board that only listens arrive 58 of 60; with both boards in chat and one of them
silent, 74 of 80. Where the remaining losses come from is still open.

No line ever arrived corrupted or twice. B -> A gets better as board B gets quieter, because on the
course bench that path has no splitter and overdrives board A's receiver at 71 dB. With board A only
listening, board B's messages arrived 35 of 40 at -30 dB and 40 of 40 at -50 dB. Hence the script's
default of -50 dB for board B.

## Exercises

1. Why does `zmbox chat` repeat TX_START, and why does it check TX_BUSY rather than TX_DONE?
2. A sending board receives its own message back. Where does that copy come from, and why is it
   harmless to throw it away?
3. All three faults above were present during Lab 11.49, which delivered 498 of 500. For each, say
   what in the one-way setup hid it.
4. A chat line holds at most 24 characters after the name. Where does that limit come from, and what
   would a longer message need?

<details markdown="1">
<summary>Answers</summary>

1. The mailbox refuses TX_START while it listens, and a listening attempt that has already begun
   runs to its end (up to 136 ms) even after RX_STOP. So the first TX_START may be refused, and the
   program tries again until the mailbox takes it. TX_DONE stays set after the previous message, so
   it cannot tell a new start from an old one; TX_BUSY rises only when this start was taken.
2. TX_START sends and receives in one attempt, and the board's receiver hears its own burst through
   the leakage between TX and RX on the board. The copy says nothing about whether the other board
   received the line, so it carries no information for the chat.
3. The halved burst: Lab 11.49 never ran `zmsg` after `zmbox` on the same board, so the DAC sources
   were never left on four channels. The calibration blast: board A sent with `zmsg`, which already
   wrote its settings only when they changed. The listening board's frames: board B listened with
   its TX LO off, so they never left the chip.
4. Packet-v1 has 27 payload bytes (256 whitened bits per frame), and the chat spends three on
   "A: ". A longer message needs either a longer frame or several packets with a sequence number and
   reassembly on the receiving side, plus a decision about what to do when one of them is lost.

</details>

## Evidence

- [`two-board-chat-20261016.md`](https://github.com/Lay007/zynq-sdr-course/blob/main/reports/hardware/two-board-chat-20261016.md):
  all four findings, the images and the numbers;
- issues [#67](https://github.com/Lay007/zynq-sdr-course/issues/67) and
  [#69](https://github.com/Lay007/zynq-sdr-course/issues/69).

## What this lab does and does not show

It shows two boards exchanging typed messages through the Lab 5.12 register contract in both
directions, with the link layer in the fabric and no corrupted message. It does not show a
reliable link: a few lines in a hundred are lost, there is no acknowledgement and no
retransmission, and the cause of the remaining losses was not found. All numbers are from one board
pair, one carrier, conducted paths.
