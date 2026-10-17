# Two-board link layer: delivery vs level, collisions, fragments, speed (2026-10-17)

Follow-up of [two-board-arq-20261017.md](two-board-arq-20261017.md). Four questions about the chat
with acknowledgements (`zmbox chat --arq`), measured on the course bench: how delivery depends on
the signal level, what happens when both boards talk at once, how long messages travel in
fragments, and how fast the link is and why. Raw data, including every console line used here:
[`two-board-link-layer-20261017.json`](two-board-link-layer-20261017.json).

Bench: board A TX1 -> variable attenuator (30 dB) -> splitter -> board B RX1; board B TX1 -> 30 dB
-> board A RX1; 915 MHz, RX manual 71 dB. Both boards on `issue70-listen-window` (md5 `bee0ba19`).
`zmbox` from 7742f13 (the level sweep: fe321c7, the same protocol without the random back-off).

## Delivery against the TX level

Board B 21 dB below board A throughout (the B -> A path has no splitter), 40 lines per point and
mode:

| board A / B TX, dB | A -> B without | A -> B with `--arq` | B -> A without | B -> A with `--arq` | lines reported not acknowledged, A / B |
|---|---:|---:|---:|---:|---:|
| -44 / -65 | 39 | 40 | 40 | 40 | 0 / 0 |
| -47 / -68 | 39 | 40 | 32 | 40 | 0 / 0 |
| -50 / -71 | 28 | 40 | 19 | 40 | 1 / 0 |
| -53 / -74 | 15 | 26 | 2 | 20 | 36 / 37 |
| -56 / -77 | 3 | 2 | 0 | 0 | 40 / 40 |

![Lines delivered against the TX level, with and without acknowledgements](../../docs/assets/lab11_51_arq_vs_level.png)

Down to -50/-71 dB the acknowledgements turn a link that loses up to half of the lines into one
that delivers all of them. At -53/-74 they still help (26 instead of 15, 20 instead of 2), but almost
every line is reported as not acknowledged, including the 26 that board B printed. The
acknowledgements for board A's lines travel from B to A, and that direction delivered 2 of 40 lines
on its own: a protocol that needs answers is only as good as the weaker of the two directions. At
-56/-77 nothing gets through either way.

## Both boards typing at the same moment

Both boards type a line at the same moment, every 4 s, 40 rounds:

| levels A / B, dB | random back-off | A -> B | B -> A | lines needing a repeat, A / B |
|---|---|---:|---:|---:|
| -30 / -50 | off | 40 | 40 | 2 / 36 |
| -30 / -50 | on | 40 | 40 | 3 / 37 |
| -47 / -68 | off | 40, 40 | 40, 40 | 6, 8 / 36, 36 |
| -47 / -68 | on | 40, 40 | 40, 40 | 8, 7 / 37, 34 |

No line was lost. Almost every line of board B needed one repeat, board A's lines rarely; why the
collision costs board B and not board A was not investigated. The random back-off (up to 0.5 s
added to the 0.6 s wait before a repeat) made no measurable difference: after the first collision
the two boards are no longer in step, so the repeats do not keep meeting. The back-off stays in
`zmbox`, since it cannot hurt; this bench just does not need it.

## Long messages in fragments

A line longer than one packet goes out in fragments of up to 24 text bytes, each acknowledged on
its own, at most 16 (384 bytes). Results per direction (the sender's view in brackets where it
differs):

| message | levels A / B, dB | A -> B | B -> A | repeats A / B | time per message (median) |
|---|---|---:|---:|---:|---|
| 103 B, 5 fragments | -30 / -50 | 20 of 20 | 20 of 20 | 0 / 0 | 1.45 s |
| 384 B, 16 fragments | -30 / -50 | 10 of 10 | 10 of 10 | 0 / 0 | 4.6 s |
| 103 B, 5 fragments | -47 / -68 | 20 of 20 | 20 of 20 | 15 / 8 | 2.2 s / 1.4 s |
| 103 B, 5 fragments | -50 / -71 | 16 of 20 (14) | 20 of 20 | 103 / 70 | 7.0 s / 5.4 s |

No message was ever assembled wrong. On the lossiest link two of board A's messages arrived whole
while board A reported them as not delivered: the acknowledgement of the last fragment was lost.

A first run with 384-character lines reported all 20 messages as wrong. The test was at fault: 384
characters plus "A: " exceed the 384-byte limit, so the sender cut the message, and the receiver
printed exactly what was sent. The rows above use 381 characters.

## How fast, and why

Time from sending a line to its acknowledgement, 40 lines each way, -30/-50 dB:

| | minimum | median | maximum |
|---|---:|---:|---:|
| with the 140 ms wait before every send (default) | 283 ms | 292 ms | 302 ms |
| without it (`ZMBOX_TX_DELAY_MS=0`) | 141 ms | 210 ms | 274 ms |

With the wait the time is almost constant: the sender waits 140 ms, the receiver waits 140 ms before
its acknowledgement, and the rest (two bursts of 0.49 ms, the reception, the mailbox polling) is
about 12 ms. Without the wait it drops less than expected, because each side then waits for the
listening attempt in flight to end instead: the mailbox does not take TX_START while an attempt
runs, and RX_STOP does not cut it short. The sender's attempt is at a random point of its 136 ms
window. The receiver has just restarted its attempt after receiving the line, so its
acknowledgement waits almost a whole window. Explanation from the numbers; the attempts were not
observed directly.

A 384-byte message in 16 fragments takes 4.6 s with the wait (about 84 B/s) and 4.35 s without it
(about 88 B/s): about 280 ms per fragment, of which the radio is busy for twice 0.49 ms. On the
air, a burst carries 27 payload bytes in 0.49 ms; the link spends more than 99 % of its time
waiting. A mailbox that ended a listening attempt at RX_STOP would bring a fragment's cycle down
from about 280 ms to tens of milliseconds; that is an RTL change, not made here (#71).

## Limits

- One board pair, one carrier, conducted paths; one or two runs per row, 10 to 40 messages each.
- The losses at low levels were not split by cause (weak signal, a receiver busy with its own
  transmission, collisions).
- The latency explanation rests on the timing figures and the mailbox contract; the listening
  attempts were not traced.
