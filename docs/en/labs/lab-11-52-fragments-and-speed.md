# Lab 11.52 — Long messages, and why the link is so slow

## Idea

A packet of Lab 11.49 carries 27 bytes, and a chat line in Lab 11.51 is cut at 24 characters after
the name. Longer messages need fragments: cut the text into pieces, number them, send each one with
the acknowledgements of Lab 11.51, and put them back together on the other side. That is a page of
C.

Timing the fragments raises the second question of this lab. A burst lasts half a millisecond, yet
a 384-byte message takes four and a half seconds: the link spends more than 99 % of its time
waiting. Where the time goes is a good exercise in reading a protocol against a clock, and the
answer is not in the radio.

## Fragments

```text
payload of a fragment:   0x1E | message id | index << 4 | count - 1 | up to 24 text bytes
```

- **The first byte marks a fragment.** `0x1E` (ASCII RS, record separator) cannot start a typed
  line, just like the `0x06` of an acknowledgement, so the receiver tells the three kinds of frame
  apart by the first byte.
- **The message id** says which message a fragment belongs to. When a fragment of a new id arrives,
  whatever was left of the old one is dropped.
- **Index and count** fit in one byte: at most 16 fragments of 24 bytes, 384 bytes per message.
- **Every fragment is an ordinary acknowledged frame** with its own sequence number. If one is not
  acknowledged after 5 tries, the sender gives up on the whole message and says which fragment
  failed. The receiver prints a message only when all its fragments are in.

Fragments are part of `zmbox chat --arq`: a longer line simply goes out in pieces.

```text
board-a$ ./zmbox chat --name A --arq --tx-gain -30
board-b$ ./zmbox chat --name B --arq --tx-gain -50
```

On the course bench (the boards and paths of Lab 11.50, image `issue70-listen-window`), counted with
the chat script and lines padded to a given length:

```bash
cd blocks/block_11_integrated_sdr_project/python
python two_board_chat.py --rounds 10 --arq --line-len 381 --period 10 --json-out long.json
```

| message | levels A / B, dB | A -> B | B -> A | repeats A / B | time per message (median) |
|---|---|---:|---:|---:|---|
| 103 B, 5 fragments | -30 / -50 | 20 of 20 | 20 of 20 | 0 / 0 | 1.45 s |
| 384 B, 16 fragments | -30 / -50 | 10 of 10 | 10 of 10 | 0 / 0 | 4.6 s |
| 103 B, 5 fragments | -47 / -68 | 20 of 20 | 20 of 20 | 15 / 8 | 2.2 s / 1.4 s |
| 103 B, 5 fragments | -50 / -71 | 16 of 20 | 20 of 20 | 103 / 70 | 7.0 s / 5.4 s |

No message was ever put together wrong. On the lossiest link board A reported only 14 of its
messages as delivered, while board B printed 16: twice the acknowledgement of the last fragment was
lost. A message of many fragments is as fragile as its weakest fragment, and the ambiguity of Lab
11.51 applies to it as a whole.

The first run of the 384-byte case reported every message as wrong. The test was at fault, not the
protocol: 384 characters plus "A: " are 387 bytes, the sender cut them to 384, and the receiver
printed exactly what was sent. With 381 characters every message arrived. When a test fails all at
once, check the test first.

## Where the time goes

Time from sending one line to its acknowledgement, 40 lines each way, levels -30/-50 dB:

| | minimum | median | maximum |
|---|---:|---:|---:|
| `zmbox chat --arq` as it is (140 ms wait before every send) | 283 ms | 292 ms | 302 ms |
| without that wait (`ZMBOX_TX_DELAY_MS=0`) | 141 ms | 210 ms | 274 ms |

With the wait, the time is nearly constant and adds up: the sender waits 140 ms, the receiver waits
140 ms before its acknowledgement, and everything else is about 12 ms. The two bursts take 0.49 ms
each. The 140 ms wait was added in Lab 11.50 to keep bursts away from the edge of the other board's
listening window; with the receiver fixed in `issue70-listen-window` it is no longer needed for that.

Dropping it saves less than expected, and the reason is the mailbox contract. The mailbox does not
take TX_START while a listening attempt runs, and RX_STOP does not cut the attempt short, so a send
waits for the end of the current 136 ms window. The sender's attempt is at a random point of its
window. The receiver has just restarted its attempt after receiving the line, so its acknowledgement
waits almost a whole window. Together that comes to about 140 to 270 ms. (This explanation is read
from the numbers and the contract; the attempts themselves were not traced.)

The same holds for long messages. A 384-byte message took 4.6 s with the wait and 4.35 s without it,
84 and 88 bytes per second, about 280 ms per fragment. On the air a fragment takes 0.49 ms. The link
waits more than 99 % of the time, and the cure is in the fabric: a mailbox whose RX_STOP ends the
listening attempt at once would bring a fragment down to tens of milliseconds. That is an RTL change
still to be made (issue #71).

## Exercises

1. Why can the receiver drop the leftovers of an unfinished message as soon as a fragment with a new
   message id arrives, instead of keeping several messages in parallel?
2. Board A reported 14 messages delivered, board B printed 16. Which fragment's acknowledgement must
   have been lost, and why that one?
3. A message of n fragments travels over a link where each fragment gets through all 5 tries with
   probability p. What is the chance that the whole message arrives? What does that say about
   choosing the fragment size?
4. Estimate the time per fragment if RX_STOP ended the listening attempt at once. What would then
   limit the speed?

<details markdown="1">
<summary>Answers</summary>

1. The sender sends one message at a time and moves on only when every fragment is acknowledged or
   it gives up. A fragment with a new id therefore means the old message is finished on the
   sender's side, one way or the other, and its missing fragments will never come.
2. The last one. Board B prints the message when its last fragment arrives, and board A counts the
   message as delivered only when that fragment is acknowledged. Any earlier fragment whose
   acknowledgement was lost would have been repeated, and the repeat acknowledged, before the next
   fragment went out.
3. p to the power n. Sixteen fragments at p = 0.95 make 0.44; five make 0.77. Smaller fragments mean
   more of them and a lower chance for the whole; larger frames are each more likely to be hit by an
   error. Real links pick the frame size for the channel, and some adapt it.
4. Without the waits, a fragment costs two bursts (about 1 ms), the reception and the copy into the
   mailbox, and the software polling (`zmbox` polls every 2 ms while it waits, every 20 ms while
   idle): a few to tens of milliseconds, ten times faster or more. Then the stop-and-wait itself
   limits it, since the sender is idle while the acknowledgement travels; sending the next fragments
   before the acknowledgements come back (a window) would be the next step.

</details>

## Evidence

- [`two-board-link-layer-20261017.md`](https://github.com/Lay007/zynq-sdr-course/blob/main/reports/hardware/two-board-link-layer-20261017.md):
  fragments, latency and speed, with every console line in the JSON next to it;
- issue [#71](https://github.com/Lay007/zynq-sdr-course/issues/71): RX_STOP and the waiting.

## What this lab does and does not show

It shows messages of up to 384 bytes carried in acknowledged fragments and reassembled without a
single wrong message, and it shows where the time of a stop-and-wait link goes. It does not show a
fast link: the link runs at under 100 bytes per second, waiting more than 99 % of the time, until
the mailbox changes. One board pair, one carrier, conducted paths, 10 to 40 messages per row.
