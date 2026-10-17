# Two-board chat with acknowledgements (Lab 11.51), 2026-10-17

The chat of Lab 11.50 sends every line once. On a good link that is enough (100 of 100 at the
default levels), but the link has no way to say that a line was lost. `zmbox chat --arq` adds the
simplest link-layer fix: the receiver answers every line with an acknowledgement, and the sender
repeats the line until one arrives. This report covers the protocol, the bench results, and what
the acknowledgements cannot do. Raw data: [`two-board-arq-20261017.json`](two-board-arq-20261017.json).

Bench as in [two-board-chat-20261016.md](two-board-chat-20261016.md): board A TX1 -> variable
attenuator (30 dB) -> splitter -> board B RX1; board B TX1 -> 30 dB -> board A RX1; 915 MHz, RX
manual 71 dB. Both boards on `issue69-listen-silent` (md5 `2f5cc35d`); `zmbox` from fe321c7.

## Protocol

- **Acknowledgement frame.** A packet-v1 frame with a one-byte payload, `0x06` (ASCII ACK), and
  the sequence number of the line it acknowledges. A chat line cannot start with that byte, so the
  receiver tells the two apart without a type field.
- **Sender.** After a line goes out it listens for 0.6 s for the acknowledgement with that sequence
  number; without one it sends the line again, at most 5 times. It prints the line once, with
  "acknowledged after a repeat" or "no acknowledgement after 5 tries" when that applies. A line
  from the other board that arrives while it waits is handled normally.
- **Receiver.** It acknowledges every copy it receives, because its earlier acknowledgement may
  have been the frame that was lost, and prints a line only if the sequence number is new.
- **Sequence numbers** start at a random value, so that a chat restarted on one board is not taken
  for a repeat by the other.

## One-way baseline

Two 500-message runs from board A to board B (board B only listening, TX -30 dB), now started on
the boards themselves and collected over short SSH connections, because long SSH sessions between
the PC and the boards were reset in earlier runs: with the fabric modem (`zmbox send`) 500 of 500,
with the host-built DMA burst (`zmsg send --once`) 498 of 500, no wrong message.

## A link that loses lines

To see the acknowledgements work, both transmitters were turned down until about 40 % of the
lines were lost (board A TX -50 dB, board B TX -71 dB; the B -> A path has no splitter and needs
21 dB less). Two runs each, 100 rounds in total:

| | A -> B | B -> A |
|---|---:|---:|
| without `--arq` | 60 of 100 | 61 of 100 |
| with `--arq` | **100 of 100** | **99 of 100** |

With `--arq` 52 of board A's lines and 45 of board B's needed at least one repeat. No line arrived
corrupted, and none was printed twice. At the default levels (A -30 dB, B -50 dB) `--arq` gave
30 of 30 both ways with 4 repeats.

## What the acknowledgements cannot do

The sender reported "no acknowledgement after 5 tries" 8 times in the 100 lossy rounds. Seven of
those lines had arrived: the line got through, the acknowledgements did not. The sender cannot
tell these two cases apart, because a missing acknowledgement looks the same either way. Only one
line of 200 was really lost.

A short scripted exchange on the lossy link shows all three outcomes:

```text
board A                                                   board B
>> A: hello, B here?                                      << A: hello, B here?
<< B: yes, hearing you, A                                 >> B: yes, hearing you, A   (acknowledged after a repeat)
>> A: loud and clear   (no acknowledgement after 5 tries)
<< B: what carrier?                                       >> B: what carrier?   (acknowledged after a repeat)
>> A: 915 MHz, conducted   (acknowledged after a repeat)  << A: 915 MHz, conducted
<< B: nice. signing off                                   >> B: nice. signing off
>> A: bye   (acknowledged after a repeat)                 << A: bye
```

"loud and clear" never reached board B, and board A said so. Board B typed its next line during
those 5 tries, so both boards were sending in the same seconds. The modem is half duplex: while a
board transmits and hears its own burst it cannot receive. Whether the collisions cost more than
the attenuation here was not measured.

## Limits

- One board pair, one carrier, conducted paths, two runs per row.
- The repeat timing is fixed (0.6 s); with both boards talking at once, the repeats of the two
  boards can keep colliding. A random back-off would avoid that; it is not implemented.
- The losses at TX -50/-71 dB were made by turning the level down, but they were not split by
  cause: weak signal, a receiver busy with its own transmission, and the window edge of #70 all
  count together.
