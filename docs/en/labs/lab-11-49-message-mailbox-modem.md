# Lab 11.49 — The mailbox talks to the modem

## Idea

Lab 5.12 put a small mailbox between the processor and the fabric: the PS writes a message into
registers, sets TX_START, and the fabric copies it into the RX registers, where the PS reads it
back. An echo, on purpose: the whole PS/PL transaction is visible and nothing else can go wrong.
The lab ended with a promise that the same registers would later carry a message through the QPSK
modem.

This lab keeps that promise. A program on the board does exactly what it did in Lab 5.12, but
behind the registers the fabric now builds a radio packet, transmits it, receives it, checks it and
hands it back. A second register bit lets the same mailbox wait for a message that another board
sends. The interesting part is less the code than where each job ended up, and why.

## Who does what

```text
PS (zmbox)          TX_SEQUENCE, TX_LENGTH, TX_DATA, TX_START ... STATUS.RX_VALID, RX_*, RX_ACK
                      |                                               ^
mailbox (CPU clock)   packet-v1: length, sequence, payload, CRC-16    | de-whiten, check CRC,
                      PN9 whitening                                   | fill RX_* (CRC_OK / FRAME_ERROR)
                      |  256 bits + toggle                            |  256 bits + toggle
bridge (sample clk)   burst head, preamble, packet bits               | copy the decoded payload bits
                      -> QPSK modem TX                                | when the attempt ends
                      |                                               |
                      +------ DAC -> TX1 ~~~ RF ~~~ RX1 -> ADC ------> receiver (Lab 11.45 chain)
```

- **The link layer lives in the mailbox.** Packet-v1 (the format of Lab 11.46 and `zmsg`), the
  CRC and the PN9 whitening are computed in the fabric, in the CPU clock domain, next to the
  registers they serve. The modem never learns that its 256 bits are a packet.
- **The physical layer lives in the modem.** The transmitter sends the burst head of Lab 11.48
  (training symbols and the reference symbol), the 48-bit preamble from the frame ROM, then the
  256 packet bits. The receiver is the Lab 11.45 chain, unchanged.
- **The bridge only starts attempts and hands bits back.** A request from the mailbox starts an
  attempt just like the start bit in `gp_ctrl` does; when the attempt ends, the bridge copies the
  decoded payload out of its decoded-bit register.
- **Two clock domains, toggles in between.** The mailbox runs on the CPU clock, the modem on the
  sample clock. Each request and each answer is a toggle plus a data word that is stable before the
  toggle changes and stays stable after it. A pulse would not do: Lab 11.48 found that a start pulse
  made of two quick register writes is lost in a two-flop synchronizer about once in seven times.

## Registers

Everything from Lab 5.12 stays, at the base address 0x79050000:

| offset | register | in this lab |
|---|---|---|
| 0x00 | ID | `0x4D424F58` ("MBOX"), unchanged |
| 0x04 | VERSION | `0x00020000` (the echo is `0x00010000`); `0x00020001` when RX_STOP also ends the listening attempt in flight (issue #71) |
| 0x08 | CONTROL | bit 0 TX_START, bit 1 RX_ACK as before; **bit 2 RX_LISTEN, bit 3 RX_STOP** |
| 0x0C | STATUS | bits 0-3 as before (TX_BUSY, TX_DONE, RX_VALID, RX_OVERFLOW); **bit 4 LISTENING** |
| 0x10, 0x14 | TX_SEQUENCE, TX_LENGTH | at most 27 bytes; a longer message is not sent and completes with FRAME_ERROR |
| 0x20-0x5C | TX_DATA | payload bytes, little-endian in the words |
| 0x60-0x68 | RX_SEQUENCE, RX_LENGTH, RX_META | RX_META bit 0 CRC_OK, bit 1 FRAME_ERROR (no frame, or a length out of range) |
| 0x70-... | RX_DATA | the received payload, zero beyond RX_LENGTH |

TX_START sends the message and receives whatever comes back in the same attempt: on one board with
TX1 cabled to RX1 that is the board's own burst, so the mailbox works like the echo of Lab 5.12,
only through the radio. RX_LISTEN makes the mailbox wait for messages from elsewhere: the bridge
runs listening attempts (the listen mode of Lab 11.48) one after another, frames with a matching CRC
land in the RX registers, anything else is dropped. TX_START is refused while the mailbox listens.

The mailbox is not a separate block in the block design. It sits inside the bridge's wrapper and
adds one AXI-Lite slave to the CPU interconnect, so the 256-bit buses never leave one module. The
wrapper passes only the low 8 address bits to the core, because the interconnect hands over the
full address: the trap of Lab 5.12.

## Without hardware

```bash
python tools/run_block5_hdl_smoke.py --test tb_message_modem_loopback --test tb_message_modem_listen
```

`tb_message_modem_loopback` drives the wrapper at the board address with the DAC looped back to
the RX tap, sends an 18-byte message and expects it back with CRC_OK; it also checks that a
30-byte message completes at once with FRAME_ERROR. `tb_message_modem_listen` connects two copies
of the wrapper: T sends two messages, R listens and must deliver both. R's ADC gets T's burst while
T transmits and a little noise otherwise, because the packet detector of the listen mode learns
the noise level from the silence. (The first version of this testbench built that noise one bit
too narrow, so the "noise" was almost full scale; the receiver caught the first message by luck and
lost the second. The fix was in the testbench, not in the design.)

## Two boards: a message from board A lands in board B's mailbox

Bench as in Lab 11.48: board A TX1 -> 30 dB -> splitter -> board B RX1, 915 MHz. Board B needs the
image `issue55-mailbox-listen` from the artifacts repository (sha256 `530e0571...`). Board B runs
from a RAM disk, so `zmsg` and `zmbox` have to be copied to `/root` again after every reboot,
including the one that loads a new image.

```text
board-b$ ./zmbox listen --count 3 --timeout 30
board-a$ ./zmsg stop
transmitter stopped
board-a$ ./zmsg send "into the mailbox 0" --seq 70 --once --tx-gain -30
TX once sequence=70 bytes=18 payload="into the mailbox 0" lead=64
board-a$ ./zmsg send "into the mailbox 1" --seq 71 --once --tx-gain -30
TX once sequence=71 bytes=18 payload="into the mailbox 1" lead=64
board-a$ ./zmsg send "into the mailbox 2" --seq 72 --once --tx-gain -30
TX once sequence=72 bytes=18 payload="into the mailbox 2" lead=64
board-b:  RX sequence=70 bytes=18 meta=CRC_OK payload="into the mailbox 0"
board-b:  RX sequence=71 bytes=18 meta=CRC_OK payload="into the mailbox 1"
board-b:  RX sequence=72 bytes=18 meta=CRC_OK payload="into the mailbox 2"
board-b:  listened 5.9 s, delivered 3, overflows seen 0
```

`zmbox listen` writes RX_LISTEN, then only polls STATUS.RX_VALID, reads RX_SEQUENCE, RX_LENGTH,
RX_META and RX_DATA, and writes RX_ACK. It never sees a bit of the radio frame: the de-whitening and
the CRC check happened in the fabric. `zmsg receive --listen` from Lab 11.48 does the same work on
the PS, reading the decoded bits and checking the CRC in software.

```bash
cd blocks/block_11_integrated_sdr_project/python
python two_board_zmsg_once.py --messages 500 --receiver zmbox --json-out mailbox_listen.json
```

On the course bench, board B at 71 dB:

| TX | receiver | sent | delivered | wrong message accepted |
|---:|---|---:|---:|---:|
| -30 dB | mailbox (`zmbox listen`) | 500 | 498 | 0 |
| -30 dB | PS software (`zmsg receive --listen`) | 500 | 498 | 0 |
| -50 dB | mailbox (`zmbox listen`) | 200 | 168 | 0 |

Moving the link layer into the fabric costs nothing: the same 498 of 500 either way.

## One board: the mailbox sends and gets its own message back

Bench as in Lab 11.47: board B TX1 -> attenuators (at least 30 dB; on the course bench a variable
attenuator at 0 dB, 30 dB and the splitter) -> board B RX1. `zmbox send` sets up the radio the way
Lab 11.47 does (DAC channels to the DMA input, a cyclic buffer of zeros for the DAC FIFO, LOs and
gains), then uses only the mailbox registers.

```text
board-b$ ./zmbox send 'Hello from the mailbox' --seq 17 --tx-gain -20
TX sequence=17 bytes=22 payload="Hello from the mailbox"
RX sequence=17 bytes=22 meta=CRC_OK payload="Hello from the mailbox"
board-b$ ./zmbox send 'this message is too long for packet v1' --seq 18 --tx-gain -20
payload is 38 bytes; the mailbox modem sends at most 27 (expect FRAME_ERROR)
TX sequence=18 bytes=38 payload="this message is too long for packet v1"
RX sequence=0 bytes=0 meta=FRAME_ERROR payload=""
board-b$ ./zmbox stop
transmitter stopped
```

`--count N` repeats the message N times with increasing sequence numbers and prints how many came
back. On the course bench, board B at 60 dB, 200 messages per point:

| TX gain | 0 | -10 | -20 | -30 | -35 | -38 | -40 | -42 | -45 | -50 | -60 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| CRC_OK of 200 | 163 | 200 | 199 | 199 | 200 | 198 | 80 | 19 | 13 | 125 | 1 |

At TX -20 dB a long run delivered 5000 of 5000. No message was ever accepted with a wrong payload.

Two things in that table are worth a look. At 0 dB the receiver is probably overloaded (60 dB of
gain behind about 35 dB of path loss). And between -40 and -50 dB the curve is not monotonic: it
collapses at -42 to -45 dB and partly recovers at -50. The TX attenuator is accurate (it was measured
for issue #29), so look elsewhere. Before the cable was connected, board B already received its own
burst through some leakage on the board, at a level that hardly followed the TX gain. With the cable
in place there are two paths with different delays, and around -42 dB they are about equally
strong: that would behave like two-path fading. This explanation fits the numbers but was not
checked.

## Exercises

1. Lab 5.12 promised that the same program would work with the modem behind the registers. Which
   registers does `zmbox send` use, and which of them did the modem change? What did the version
   register buy?
2. Why are the request and the answer between the mailbox and the bridge toggles with stable data,
   and not pulses? What exactly would go wrong with a one-clock pulse from the CPU clock domain?
3. While listening, the mailbox drops frames whose CRC does not match without telling the PS. Give
   one reason to keep it that way and one reason to count them in a register.
4. RX_VALID stays set until RX_ACK. What happens when two messages arrive before the PS
   acknowledges the first, and how does the PS find out?

<details markdown="1">
<summary>Answers</summary>

1. TX_SEQUENCE, TX_LENGTH, TX_DATA, CONTROL (TX_START, RX_ACK), STATUS, RX_SEQUENCE, RX_LENGTH,
   RX_META and RX_DATA, exactly the Lab 5.12 set. What changed is what they mean in time and in
   detail: TX_LENGTH is now limited to 27 bytes (the packet-v1 payload), RX_META can say
   FRAME_ERROR because a radio frame can be lost, and the answer takes milliseconds instead of one
   clock. VERSION (`0x00020000` against `0x00010000`) lets a program tell which mailbox it is
   talking to before it relies on any of that.
2. The CPU clock and the sample clock are unrelated. A one-clock pulse can fall between two edges of
   the other clock and never be seen; Lab 11.48 lost about one start in seven exactly that way. A
   toggle keeps its new level until the next request, so the synchronizer always sees the change,
   and the data next to it is stable long before and after, so it can be sampled without its own
   synchronizer.
3. Keeping it simple: almost all of those frames are false locks on noise (about 0.1 per second of
   listening, Lab 11.48), so reporting them would mostly report noise. Counting them: a rising count
   while expected messages do not arrive tells the user that the link is marginal rather than
   silent.
4. The mailbox keeps the first message and sets RX_OVERFLOW (STATUS bit 3); the second one is lost.
   The PS sees the overflow bit when it reads STATUS, and RX_ACK clears both. A receiver that has to
   keep up with bursts needs a queue, which this mailbox deliberately does not have.

</details>

## Evidence

- [`message-modem-20261015.md`](https://github.com/Lay007/zynq-sdr-course/blob/main/reports/hardware/message-modem-20261015.md):
  the design, the simulations, both images and the board results;
- [`single-message-corruption-20261015.md`](https://github.com/Lay007/zynq-sdr-course/blob/main/reports/hardware/single-message-corruption-20261015.md):
  why the lead-in became 64 symbols;
- issue [#55](https://github.com/Lay007/zynq-sdr-course/issues/55).

## What this lab does and does not show

It shows the Lab 5.12 register contract carrying real radio messages: received from another board
straight into the mailbox, with the packet checked in the fabric, as reliably as the software
receiver. It does not show a queue (one message at a time), and it uses the Lab 11.45 receiver with
its limits (Lab 11.48: listening needs pauses between packets). All numbers are from one board pair,
one carrier, a conducted path.

[Lab 11.50](lab-11-50-two-board-chat.md) runs the mailbox in both directions at once, as a chat
between the two boards, and finds three faults that the one-way setup of this lab hid.
