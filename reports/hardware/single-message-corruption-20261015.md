# Why single messages were corrupted more often than ROM frames, 2026-10-15

Question from [qpsk-listen-mode-20261015.md](qpsk-listen-mode-20261015.md): with the listen mode and
a 32-symbol lead-in, single-shot `zmsg` messages were lost about 1 % of the time at TX -30 dB, and
the lost ones were mostly received with a few wrong bits; ROM frames in the long cyclic run (one
frame every 20 frame lengths) were corrupted only 0.14 % of the time. Bench: board A TX1 -> 30 dB
-> splitter -> board B RX1, 915 MHz, TX -30 dB, board B at 71 dB manual, listen mode. Raw data:
[`single-message-corruption-20261015.json`](single-message-corruption-20261015.json).

Two things differ between the two cases: the content (random whitened packet bits against the ROM
frame) and the silence before each burst (0.9 s against 6.3 ms). Frames whose CRC or payload check
fails with about half the bits wrong are false locks on noise (0.1 per second of listening, see the
listen-mode report) and are counted separately; "corrupted" below means a real frame with a few
wrong bits.

| run | content | silence before a burst | lead-in | corrupted |
|---|---|---:|---:|---:|
| long run of the listen-mode report | ROM frame | 6.3 ms | 32 | 0.14 % (14 of 10 000 not clean) |
| E2 | message | 6.3 ms | 32 | 0.13 % (4 of 3004) |
| E1 | ROM frame | 0.3 s | 32 | 0.46 % (3 of 657) |
| E3 | message | 0.3 s | 32 | 0.30 % (3 of 1003) |
| E3 | message | 0.3 s | 64 | 0 of 1000 |
| E3 | message | 0.3 s | 128 | 0 of 1000 |
| single-shot `zmsg`, earlier | message | about 0.9 s | 32 | about 1 % (lost: 6 and 10 of 500) |
| single-shot `zmsg` | message | about 0.9 s | 64 | lost: 2 of 500 |

- **The content does not matter**: the same 6.3 ms of silence gives 0.13 % with a message and
  0.14 % with the ROM frame.
- **The length of the silence does**: 0.13 % after 6.3 ms, 0.3-0.46 % after 0.3 s, about 1 % after
  0.9 s.
- **A longer lead-in removes it**: with 64 or 128 training symbols no frame of 1000 was corrupted
  after 0.3 s of silence, and single-shot messages lost 2 of 500 instead of 6-10.

What the lead-in gives the receiver time for is not established. A plausible mechanism: during a
long pause the carrier phase between the two boards wanders, and the Costas loop, which runs only
its quiet tracking gain in differential mode, needs more than 32 symbols to catch up; after 6 ms
the phase has hardly moved. Not checked: the phase at the start of the frame was not recorded.

The numbers are small (single to low double digits of corrupted frames), so the differences between
neighbouring rows are rough; the step from 32 to 64 symbols is consistent across both kinds of run.
The lead-in is now 64 symbols by default in `zmsg`, `two_board_message.once_iq`,
`two_board_zmsg_once.py` and the fabric message source (`qpsk_message_dibit_source`).
