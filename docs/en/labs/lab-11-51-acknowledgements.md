# Lab 11.51 — Acknowledgements: the sender learns what was lost

## Idea

The chat of Lab 11.50 sends every line once and hopes. On the course bench at its default levels
that is enough, but turn the transmitters down and lines start to vanish without a trace: the
sender prints `>>`, the other board prints nothing, and nobody knows. This lab adds the oldest
remedy in data links. The receiver answers every line, and the sender repeats a line until the
answer comes. It takes about a hundred lines of C on top of Lab 11.50, and nothing changes in the
fabric.

The interesting part is what the answers cannot do. A sender that gets no answer cannot tell
whether its line or the answer was lost, and on the bench that ambiguity shows up in the numbers.

## The protocol

```text
sender                                      receiver
line, sequence s     ------------------>    new s?  print it
                     <------------------    ACK, sequence s      (for every copy, new or not)
no ACK within 0.6 s: send the line again, at most 5 times
```

- **The acknowledgement is a frame of its own.** It is a packet-v1 frame like any other, with a
  one-byte payload, `0x06` (ASCII ACK), and the sequence number of the line it answers. A typed
  line never starts with that byte, so the receiver tells the two kinds apart without a type field.
- **The receiver acknowledges every copy.** If its first acknowledgement was lost, the sender sends
  the line again, and a receiver that stayed silent because it had already seen the line would make
  the sender give up.
- **The receiver prints a line once.** The sequence number tells a repeat from a new line.
- **Sequence numbers start at a random value.** Otherwise a chat restarted on one board would begin
  with the numbers the other board has just seen, and its first lines would be dropped as repeats.

## What you need

The bench of Lab 11.50: two boards with the image `issue70-listen-window` (the results below were
taken with `issue69-listen-silent`), two conducted paths,
`/root/zmbox` on both boards built from `blocks/block_11_integrated_sdr_project/sw/zmbox.c`.
Acknowledgements are a mode of the same program:

```text
board-a$ ./zmbox chat --name A --arq --tx-gain -30
board-b$ ./zmbox chat --name B --arq --tx-gain -50
```

## A link that loses lines

To see the acknowledgements at work, make the link bad. On the course bench, board A at TX -50 dB
and board B at TX -71 dB lose about 40 % of the lines (the B -> A path has no splitter, so board B
needs 21 dB less). A scripted exchange at those levels, recorded on the bench:

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

(The two consoles are shown side by side; the lines were fed in by a script, so the typed text
itself does not appear.) Four lines needed a repeat and arrived. "loud and clear" did not arrive
in 5 tries, and board A said so. That is the whole gain: a lost line is no longer silent.

The same comparison, counted, with the script of Lab 11.50:

```bash
cd blocks/block_11_integrated_sdr_project/python
python two_board_chat.py --rounds 60 --tx-gain-a -50 --tx-gain-b -71 --json-out plain.json
python two_board_chat.py --rounds 60 --tx-gain-a -50 --tx-gain-b -71 --arq --json-out arq.json
```

On the course bench, two runs each, 100 rounds in total:

| | A -> B | B -> A |
|---|---:|---:|
| without `--arq` | 60 of 100 | 61 of 100 |
| with `--arq` | 100 of 100 | 99 of 100 |

With `--arq`, 52 of board A's lines and 45 of board B's needed at least one repeat. No line arrived
corrupted, and none was printed twice. At the default levels the acknowledgements cost almost
nothing: 30 of 30 lines each way, 4 repeats in all.

## When the answer is what gets lost

In those 100 lossy rounds the senders reported "no acknowledgement after 5 tries" 8 times. Only one
of those lines was really lost. The other seven had arrived, and what never got back was the
acknowledgement. The sender has no way to tell: in both cases it simply hears nothing.

This is not a bug in the chat. Over a link that can lose frames in both directions, no finite
exchange of messages lets both ends be certain of the same thing; every acknowledgement would need
an acknowledgement of its own. A protocol picks what it can promise instead. This one promises that
a line the sender reports as acknowledged has arrived, and that a lost line is never silent. It
does not promise that "no acknowledgement" means "not delivered".

## Things to try

- Type on both boards at the same moment on the lossy link. The modem is half duplex: while a board
  sends and hears its own burst, it cannot receive. Both senders repeat every 0.6 s, so their
  repeats can keep meeting. Count how often a line needs all 5 tries, and compare with lines typed
  on one board only.
- Change `ARQ_TRIES` or `ARQ_WAIT_S` in `zmbox.c`. Fewer tries lose more lines; a shorter wait sends
  repeats before the acknowledgement could have arrived (it needs at least the 140 ms wait of Lab
  11.50 plus the burst).

## Exercises

1. Why does the receiver acknowledge a line it has already printed?
2. What would go wrong if every chat started with sequence number 1?
3. A sender reports "no acknowledgement after 5 tries". What can it conclude about the line, and
   what can it not?
4. Repeats are sent at a fixed interval. Why can two boards that talk at the same time keep losing
   each other's lines, and what is the usual cure?

<details markdown="1">
<summary>Answers</summary>

1. Because its acknowledgement may be what was lost. The sender only knows that it heard nothing,
   so it sends the line again; if the receiver stayed silent about lines it already has, the sender
   would repeat until it gives up and then report a delivered line as lost.
2. After one board restarts, its first lines would carry the sequence numbers the other board has
   just printed, and the receiver would drop them as repeats. Starting at a random value makes that
   unlikely. A protocol that must exclude it altogether agrees on the numbering at the start of a
   session.
3. It can conclude only that no acknowledgement came back. The line may have been lost, or it may
   have arrived and every acknowledgement may have been lost; on the bench that happened 7 times out
   of 8. What it can rely on is the opposite case: an acknowledged line has arrived.
4. Each board stops listening while it sends. If both start a line at about the same moment and
   repeat on the same 0.6 s rhythm, each repeat can fall where the other board is transmitting. The
   usual cure is a random back-off: wait a random time before each repeat, so the two rhythms drift
   apart.

</details>

## Evidence

- [`two-board-arq-20261017.md`](https://github.com/Lay007/zynq-sdr-course/blob/main/reports/hardware/two-board-arq-20261017.md):
  the protocol, the one-way baseline and the lossy-link runs;
- [`two-board-chat-20261016.md`](https://github.com/Lay007/zynq-sdr-course/blob/main/reports/hardware/two-board-chat-20261016.md):
  the chat without acknowledgements.

## What this lab does and does not show

It shows a link layer that turns a link losing about 40 % of its frames into one that delivers 199
of 200 lines and reports the rest, with nothing changed in the fabric. It does not show a reliable
link in the strict sense: "no acknowledgement" does not mean "lost", there is no back-off for two
boards talking at once, and the losses on the bench were not split by cause. One board pair, one
carrier, conducted paths, two runs per row.
