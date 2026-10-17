# Lab 11.50 — Two boards chat through their mailboxes

## Idea

Lab 11.49 sent messages one way: board A transmitted, board B's mailbox listened. A chat needs both
directions at once. Each board listens all the time, and whenever someone types a line it stops
listening for a moment, sends the line and goes back to listening. The program is short, because
the mailbox already does the hard part. What makes this lab worth doing is what the first chat
showed: it delivered 7 lines out of 10 in each direction, and every cause had been there in the
earlier labs without showing. Each was hidden by something the one-way setup happened to do.

## How `zmbox chat` works

```text
start:        set up the radio once (LO, gains, DAC source); RX_LISTEN
loop:         STATUS.RX_VALID?  -> print "<< text" if RX_META says CRC_OK; RX_ACK
              a line on stdin?  -> RX_STOP; wait 140 ms
                                   write TX_SEQUENCE, TX_LENGTH, TX_DATA
                                   TX_START, repeated until STATUS.TX_BUSY shows it was taken
                                   wait for RX_VALID: our own burst, heard through the board; discard it
                                   print ">> text"; RX_LISTEN
```

Three details come from the mailbox contract of Lab 11.49:

- **TX_START is refused while the mailbox listens**, and RX_STOP does not cut short a listening
  attempt that has already begun (up to 136 ms). The program waits 140 ms, longer than any attempt,
  and then repeats TX_START until it is taken. Why it waits instead of simply retrying is the last
  finding below. It watches TX_BUSY, not TX_DONE: TX_DONE stays set from the previous message.
- **A sending board hears itself.** TX_START sends and receives in the same attempt, so the board's
  own burst comes back through the leakage between TX and RX on the board. The chat throws that one
  away.
- **The name goes into the payload.** Packet-v1 carries at most 27 bytes, so "A: " plus 24
  characters is all one line can hold; longer lines are cut.

## What you need

- Two boards with the image `issue70-listen-window` from the artifacts repository (sha256
  `f89db5d1...`). The chat also runs on `issue69-listen-silent`, which the results below were taken
  with; older mailbox images work for one-way messages but not for a chat (the third finding below
  explains why).
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

### Lines lost at the edge of a listening window (issue #70)

On the #69 image the chat still lost about one line in ten, again without a single CRC failure,
while each piece of the chat on its own lost almost nothing. Taking it apart showed that only one
thing mattered: whether the sender was `zmbox chat`. Board B sending from the chat reached a board
that only listened 361 times out of 400; the same board sending with `zmbox send` reached it 99 or
100 times out of 100. The bursts were not the difference. Recorded on board A, the chat's bursts
were as long as the others (1864 samples) and carried the same symbols: their symbol-to-symbol
phase steps matched those of `zmbox send` to 0.94-0.99. And the losses came in runs, lines 65, 66
and 67 in one run, so something slowly varying was at work.

The difference was the moment of sending. The chat stops listening and repeats TX_START until the
mailbox takes it, which happens when the listening attempt in flight ends: every chat burst left
at the end of the sender's 136 ms listening window. An explanation that fits the numbers: the
receiver's window restarts when a packet arrives, so after an exchange both boards' windows start
at nearly the same moment, and the next burst from the chat arrives near the end of the
receiver's window, where a packet does not fit and is lost. Messages from `zmbox send` go out at a
moment set by the program, not by a window. The receiver's windows were not observed directly.

The test was cheap: wait 140 ms after RX_STOP, longer than any attempt, and only then start. The
chat sender went from 93 and 94 of 100 to 100 of 100 twice. A 68 ms wait helped little (96 and 95),
probably because the attempt in flight often had more than 68 ms left, so the burst still left at
its end. `zmbox chat` now waits 140 ms; a line goes out 0.14 s later than it could, which nobody
notices in a chat.

The receiver was fixed as well. A listening attempt used to end when its sampler had produced
65535 symbols, whatever was arriving at that moment. Now the window is extended while a packet is
coming in. A simulation that sends a message 200 and 40 symbols before the end of the window lost
both with the old receiver and delivers both with the new one (`tb_message_modem_listen_edge`). On
the boards, with the image `issue70-listen-window` and no wait at all (`ZMBOX_TX_DELAY_MS=0`), the
chat delivered 100 of 100 lines in both directions, twice; the #69 image gave 92 and 84 in the same
run. The 140 ms wait stays in `zmbox chat`: it costs nothing and protects boards that still run an
older image.

### And the check the chat was built for (issue #67)

The DAC FIFO mux of the course image used to write the FIFO only while a burst was going out.
Without a vendor DMA stream, the DAC then held the last sample between bursts: a carrier at the LO.
Since Lab 11.47 a cyclic buffer of zeros covered that. The fix writes the FIFO on the FIFO's own
read request, zeros when there is nothing to send. Board B sent bursts with no DMA stream at all
(`ZMBOX_NO_ZERO_STREAM=1`), and board A measured the gaps. They were 40.3 dB above the noise with the
old image, as strong as the burst, and 9.8 dB with the new one, the same as with the zero stream.
That remainder is the TX LO leakage, one line 0.3 kHz from the LO.

## Results

Both boards on `issue69-listen-silent`, `zmbox chat` with the 140 ms wait, board A at TX -30 dB:

| board B TX | rounds | A -> B | B -> A |
|---:|---:|---:|---:|
| -30 dB | 60 | 59 | 53 |
| -40 dB | 60 | 60 | 60 |
| -50 dB | 100 | 100 | 100 |
| -50 dB | 100 | 99 | 99 |

No line ever arrived corrupted or twice, and no packet failed the CRC. On the way there, with the
same image but without the wait, the chat delivered 90 and 85 lines of 100 at -50 dB, and at
louder settings of board B fewer still from B to A. On the course bench the B -> A path has no
splitter, and at 71 dB board A's receiver is overdriven when board B is loud: with board A only
listening, board B's messages arrived 35 of 40 at -30 dB and 40 of 40 at -50 dB. Hence the
script's default of -50 dB for board B.

## Exercises

1. Why does `zmbox chat` repeat TX_START, and why does it check TX_BUSY rather than TX_DONE?
2. A sending board receives its own message back. Where does that copy come from, and why is it
   harmless to throw it away?
3. The first three faults above were present during Lab 11.49, which delivered 498 of 500. For
   each, say what in the one-way setup hid it.
4. A chat line holds at most 24 characters after the name. Where does that limit come from, and what
   would a longer message need?
5. Lines sent from `zmbox chat` were lost about ten times as often as the same lines sent with
   `zmbox send`, although the bursts on the air were the same. Why does a wait of 140 ms before
   TX_START fix that, and what would a fix in the receiver have to do instead?

<details markdown="1">
<summary>Answers</summary>

1. The mailbox refuses TX_START while it listens, and a listening attempt that has already begun
   runs to its end (up to 136 ms) even after RX_STOP. So the first TX_START may be refused, and the
   program tries again until the mailbox takes it (since the last finding it first waits 140 ms, so
   the first try is normally taken). TX_DONE stays set after the previous message, so it cannot tell
   a new start from an old one; TX_BUSY rises only when this start was taken.
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
5. Without the wait, the burst leaves when the sender's listening attempt ends, and the receiver's
   window started at about the same moment, so the burst lands at the end of the receiver's window
   and does not fit. After a wait longer than any attempt, the moment of sending is set by the typed
   line, so it falls at a random point of the receiver's window, where it almost always fits. A fix
   in the receiver would not end a listening attempt while a packet is coming in: when the window
   runs out with the packet detector still reporting a packet, extend the window until the frame
   is complete, or start the next attempt with that packet.

</details>

## Evidence

- [`two-board-chat-20261016.md`](https://github.com/Lay007/zynq-sdr-course/blob/main/reports/hardware/two-board-chat-20261016.md):
  all four findings, the images and the numbers;
- issues [#67](https://github.com/Lay007/zynq-sdr-course/issues/67) and
  [#69](https://github.com/Lay007/zynq-sdr-course/issues/69).

## What this lab does and does not show

It shows two boards exchanging typed messages through the Lab 5.12 register contract in both
directions, with the link layer in the fabric and no corrupted message. It does not show a
reliable link: there is no acknowledgement and no retransmission, and a line in a hundred can still
go missing. All numbers are from one board pair, one carrier, conducted
paths.

[Lab 11.51](lab-11-51-acknowledgements.md) adds acknowledgements and repeats to the chat, so that
a lost line is no longer lost silently.
