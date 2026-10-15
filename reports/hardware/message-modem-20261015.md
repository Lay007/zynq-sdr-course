# Message modem: the Lab 5.12 mailbox with the QPSK modem behind it (#55), 2026-10-15

Status: the design is built and runs on board B. Receiving a message from board A into board B's
mailbox is measured on the usual conducted bench. Sending from board B's own mailbox and receiving
it back on board B needs a cable from B TX1 to B RX1 that was not there; those numbers are
**still to be done**, and what was seen without the cable is labelled so.

## What was built

Lab 5.12 put a PS/PL mailbox in the fabric with an echo behind it and promised that a later lab
would put the modem there without changing the registers. Source commit `b0ffa65`:

- `zynq_message_mailbox_axi_lite` has `MODE = 1`. TX_START builds a packet-v1 frame from
  TX_SEQUENCE, TX_LENGTH and TX_DATA (CRC-16/CCITT-FALSE and PN9 whitening in the fabric, the same
  format as `zmsg` and `two_board_message.py`) and hands its 256 bits to the modem. When the modem
  answers, the core de-whitens the received bits, checks the CRC and fills RX_SEQUENCE, RX_LENGTH,
  RX_META (CRC_OK, or FRAME_ERROR when no frame was received or the length is out of range) and
  RX_DATA. A TX_LENGTH over 27 bytes is not sent and completes at once with FRAME_ERROR.
  `MODE = 0`, the echo, is unchanged; its testbenches pass.
- The bridge starts one burst on the mailbox's request: the burst head of Lab 11.48 (one symbol in
  state 0, 32 alternating flips, the last one the reference), the 48-bit preamble from the frame
  ROM, then the 256 packet bits (`qpsk_message_dibit_source`). The receiver is the Lab 11.45 chain,
  unchanged; when the attempt ends, the bridge copies the 256 decoded payload bits from its
  decoded-bit register to the mailbox. The clock-domain crossings are toggles with data held stable.
- The mailbox sits inside the bridge's block-design wrapper as an AXI-Lite slave, so the 256-bit
  buses stay inside one module; the block design only gains `ad_cpu_interconnect 0x79050000`.

## Simulation

`tb_message_modem_loopback` drives the wrapper the way the PS does, at the board address (the
interconnect passes the full address; only the low 8 bits reach the core), with the DAC stream
looped straight back into the RX tap. An 18-byte message comes back with CRC_OK and the same
sequence, length and bytes at 8 of 13 sampling phases of the coherent loopback (the others sit on
the edge of the eye: CRC failures or no lock); a 30-byte message completes at once with
FRAME_ERROR. Block 5 HDL smoke with the test: 44 of 44.

## Build

Image `issue55-message-modem` in the artifacts repository (sha256 `2a4cc8e9...`): default
directives, WNS +0.100 ns, WHS +0.030 ns, 86174 of 86174 nets routed, 39169 LUT (2937 more than
the #68 image, mostly the CRC and PN9 logic), DSPs and BRAM unchanged. The hardware handoff lists
`bpsk_bridge_bd/s_axi` at 0x79050000-0x7905FFFF.

## On board B, without the cable (preliminary)

`sw/zmbox.c` sends a message from board B's console using only the mailbox registers, after
setting up the radio as in Lab 11.47 (DAC channels to the DMA input, a cyclic zero buffer, LOs and
gains, the Lab 11.45 mode words). The mailbox identifies itself (`0x4D424F58`, version
`0x00020000`) and the first message came back:

```text
board-b$ ./zmbox send 'Hello from the mailbox' --seq 17
TX sequence=17 bytes=22 payload="Hello from the mailbox"
RX sequence=17 bytes=22 meta=CRC_OK payload="Hello from the mailbox"
```

Board B's TX1 was **not connected** to anything during this; the burst reached RX1 through some
leakage path on the board or in the chip. Messages per point, board B at 60 dB, board A silent
([`message-modem-leakage-20261015.json`](message-modem-leakage-20261015.json)):

| TX gain | sent | CRC_OK | CRC failed | no frame |
|---:|---:|---:|---:|---:|
| 0 dB | 200 | 199 | 0 | 1 |
| -10 dB | 200 | 187 | 10 | 3 |
| -20 dB | 200 | 27 | 145 | 28 |
| -30 dB | 200 / 50 | 0 / 9 | 1 / 25 | 199 / 16 |
| -40 dB | 200 / 50 | 100 / 0 | 75 / 0 | 25 / 50 |
| -50 dB | 50 | 15 | 22 | 13 |
| -60 dB | 50 | 5 | 24 | 21 |
| -89 dB | 50 | 0 | 1 | 49 |

No message was ever accepted with a wrong payload. Below -10 dB the result does not follow the TX
gain and is not repeatable between runs (the two -30 and -40 dB rows), so this path cannot be
used for measurements; it only shows that the whole chain, registers to RF and back, works on the
silicon. The numbers for the lab need the cable.

Regression on the same image: two-board single-shot messages of Lab 11.48 (`zmsg send --once` on
board A, `zmsg receive --listen` on board B), 100 sent, 97 delivered, none wrong.

Note: board B runs from a RAM disk, so the tools in `/root` (`zmsg`, `zmbox`) are gone after every
reboot, including the one that loads a new image, and have to be copied again.

## Receiving a message from another board into the mailbox

Source commit `1cfec38`, image `issue55-mailbox-listen` (sha256 `530e0571...`; WNS +0.100 ns,
WHS +0.039 ns, 39909 LUT). CONTROL bit 2 (RX_LISTEN) makes the mailbox listen: the bridge runs
listening attempts (listen mode of #68, forced on for these attempts) one after another; a frame
with a matching CRC goes to the RX registers under the Lab 5.12 rules (RX_VALID, RX_ACK,
RX_OVERFLOW), anything else is dropped and the next attempt starts. CONTROL bit 3 (RX_STOP) ends
it; STATUS bit 4 shows it. TX_START is refused while listening. The burst lead-in became 64 symbols
by default everywhere (fabric message source, `zmsg`, the Python tools), see
[single-message-corruption-20261015.md](single-message-corruption-20261015.md).

Simulation: `tb_message_modem_listen` connects two copies of the wrapper; T sends two messages,
R listens and delivers both. (The first version of the testbench made the background noise one bit
too narrow, which turned it into nearly full-scale values; R then caught the first message by luck
and lost the second. The fix was in the testbench.) Block 5 HDL smoke: 45 of 45.

On the bench (board A TX1 -> 30 dB -> splitter -> board B RX1, 915 MHz, board B at 71 dB): board A
sends with `zmsg send --once`, board B listens with `zmbox listen`, which only uses the mailbox
registers; the CRC check and the de-whitening happen in the fabric
(`two_board_zmsg_once.py --receiver zmbox`, raw data
[`message-mailbox-listen-20261015.json`](message-mailbox-listen-20261015.json)):

| TX | sent | delivered into the mailbox | wrong message accepted | duplicates |
|---:|---:|---:|---:|---:|
| -30 dB | 500 | 498 | 0 | 0 |
| -50 dB | 200 | 168 | 0 | 0 |

The PS-side receiver (`zmsg receive --listen`, which reads the decoded bits and checks the CRC in
software) delivered 498 of 500 under the same conditions, so moving the link layer into the fabric
costs nothing. At -50 dB the mailbox got 168 of 200; the PS-side receiver with the older 32-symbol
lead-in had 159 of 200 there.

## Still to do

- Board B TX1 -> attenuators (at least 30 dB) -> board B RX1: `zmbox send` vs TX gain, a long run.
- Lab 11.49 text (EN/RU).
