# Lab 11.48 — A receiver that waits for the packet

## Idea

In every two-board lab so far, board A transmitted without a pause: a cyclic buffer of frames,
over and over. Board B started its receiver at any moment and a frame was always on the air. A
real radio does not work like that. A message is sent once, and before and after it there is
nothing but noise.

The first time board A sent one frame followed by silence, board B caught it in proportion to how
much of the time the frame was on the air: with nineteen frame lengths of silence after each
frame, in 2 to 3 receptions out of 100. To receive such a packet, three things had to change. One
is in the receiver, two are in the packet itself, and none of them is the one you would guess
first.

## Bench

```text
board A TX1 -> attenuators (30 dB) -> 3-way splitter -> board B RX1
                                                     -> board A RX1, RTL-SDR (optional)
```

- 915 MHz, conducted. Board A runs the vendor image and transmits with `iio_writedev`.
- Board B needs the image with listen mode: `issue68-qpsk-listen-mode` in the artifacts
  repository (sha256 `3406e253...`). It is the #66 image plus one control bit, `gp_ctrl[18]`.
  With that bit at 0 the receiver behaves exactly as in every earlier lab.
- Board B has no fan. Long runs on the course bench kept it at 67-72 °C; stop above 80 °C.

The receiver runs in the Lab 11.45 mode (`0x2D630`: differential QPSK, DC blocker, Costas, Gardner
timing). Board A's buffer is built by `two_board_burst.burst_iq`: one 152-symbol frame, then a gap
of silence measured in frame lengths (`--gaps 19` means the frame is on the air one twentieth of
the time).

## Step 1. The receiver does not wait

```bash
cd blocks/block_11_integrated_sdr_project/python
python two_board_burst.py --gaps 0 1 4 19 99 --json-out burst_fixed.json
```

By default the script runs TX -30, -10 and -50 dB with board B at manual 71 dB and with the
slow-attack AGC, 100 attempts each. On the course bench (image before #68, all six settings
pooled, 600 attempts per row):

| silence after the frame | share of time with signal | frames caught |
|---:|---:|---:|
| 0 (continuous) | 1 | 99 % |
| 1 frame | 1/2 | 27 % |
| 4 frames | 1/5 | 15 % |
| 19 frames | 1/20 | 2.3 % |
| 99 frames | 1/100 | 0.7 % |

The receiver was designed for the self-OTA labs, where it transmits the frame itself and knows
that the frame comes back within a few hundred symbols. When it is armed, its symbol sampler
produces the frame length plus 256 symbols (0.85 ms) and stops. If no frame arrived in that window,
an idle watchdog ends the attempt, and the status register reads `0x81C` (done and timeout) with
zero symbols received. On a continuous stream a frame always fits into the window, which is why
no earlier lab noticed.

## Step 2. Waiting means living with noise

The obvious fix is a longer window. The sampler counter is 16 bits wide, so it can run for 65535
symbols (136 ms). In simulation that alone was not enough: every frame was found, but half of
them came out with gross errors. The reason is what the receiver does during the wait.

Between packets the receiver sees noise, and its loops keep working on it. The Gardner timing
detector outputs only the sign of its error, so on noise it adds a random +1 or -1 to its
integrator on every symbol: a random walk, and nothing pulls it back. After a few thousand symbols
the symbol rate was off by 1-2 %. The Costas frequency integrator walked the same way, by about
±2 kHz. When the packet finally came, both loops were somewhere else.

The chain already had a gate for this: the Costas loop freezes while `|I|+|Q|` of the symbol is
below a fixed threshold of 8. On board B at 71 dB that gate is useless. Its noise alone is 16 ADC
counts rms, more than enough to keep the gate open on almost every symbol. (The first version of
the burst report assumed the gate was closed in silence; measuring the noise showed otherwise.)
A fixed threshold cannot work when the noise level depends on the gain.

The listen mode therefore adds a packet detector, `qpsk_packet_detect.v`. It keeps two running
means of `|I|+|Q|`: a short one, over about 8 symbols, and a long one, over about 4096 symbols. The
long one is the noise level, because packets are short compared to it. A packet is present while
the short mean is at least 1.5 times the long one. The long mean is kept from one reception to the
next, like the DC estimate in Lab 11.41.

With the detector the receiver does two things in listen mode:

- the Gardner and Costas loops do not update while no packet is present;
- decisions reach the frame-sync correlator only while a packet is present, delayed by 16 symbols
  so that the first symbols of the packet, which arrive before the detector has made up its mind,
  are not lost, and for 64 symbols after the detector drops.

The second point is not cosmetic. The correlator locks when a 24-bit window matches the preamble
with at most one error, under four rotation hypotheses. On random bits that happens with
probability `4 * 25 / 2^24`, about 6e-6, per bit. A wait of 30 ms is about 30 000 bits, so without
the gate roughly every fifth wait would end in a "frame" made of noise.

## Step 3. The first symbol has nothing to compare with

With listen mode on, board B caught a packet in almost every reception. But in simulation it
often let one or two packets pass before catching one, and the reason was in the packet, not in
the receiver.

Differential QPSK carries the information in the phase change from one symbol to the next. Board
A's encoder starts from phase state 0. In a continuous stream the symbol before a frame is the last
symbol of the previous frame, the receiver knows it, and the first frame symbol decodes correctly.
After silence the symbol before the frame is noise. The first frame symbol then decodes to a random
dibit, wrong in three cases of four, and the frame sync needs 23 of the first 24 bits. One symbol
with phase state 0 in front of the frame fixes that (`--ref`): it is exactly what the encoder
assumed.

In simulation (board-like noise, random timing phase) the mean wait for a caught packet dropped
from 45 frame lengths without the reference to 16 with it. With the fixed window on the board, the
same symbol raised the catch rate at one frame of silence from 27 % to 35-49 %, depending on the
setting. For a
message that is sent only once this is the difference between "usually received" and "usually
lost".

## Step 4. Give the loops something to settle on

With listen mode and the reference symbol, a long run on the board gave this:

```bash
cd blocks/block_11_integrated_sdr_project/python
python two_board_burst.py --gaps 19 --ref --listen --tx-levels -30 --rx manual:71 --frames 10000 \
    --json-out soak_ref.json
```

10 000 frames locked, 9510 clean, 435 gross: 4.35 % of the frames had more than 8 of 256 payload
bits wrong. The continuous stream with the old receiver gives 0.32 % on the same bench.

`two_board_burst_errors.py` records the payload error count and the error positions of every
frame (the receiver reports errors per quarter of the payload and the first and last error index).
The gross frames had errors from the first payload bits on, and several of them had exactly the
same pattern, which is not what noise does. A simulation with a random symbol timing phase per
packet reproduced them, while the simulation with a fixed phase had shown none.

The explanation: after silence the timing and carrier loops start from where they were frozen and
need some symbols to settle. Without anything in front of the frame they settle on the preamble,
exactly on the bits the frame sync depends on. A larger timing-loop gain during the first 32
symbols of a packet seemed the natural fix and made things worse in simulation (11 gross frames of
30 instead of 8), so it was not kept. What helped was giving the loops something to settle on: 32
training symbols before the reference, alternating between phase states 2 and 0 (`--lead 32`).
Every symbol is a 180-degree flip, so the timing detector gets a transition on every symbol.

```bash
cd blocks/block_11_integrated_sdr_project/python
python two_board_burst_errors.py --gap 19 --lead 32 --frames 1000 --json-out errors_lead32.json
python two_board_burst.py --gaps 19 --lead 32 --listen --tx-levels -30 --rx manual:71 --frames 10000 \
    --json-out soak_lead32.json
```

The first prints the gross frames of the run with their error positions, if there are any. On the
course bench it printed `locked 1000/1000, clean 1000, gross 0`. The long run gave 10 000 locked,
9986 clean, 9 gross (0.09 %).

## The whole picture

Board B with image `3406e253`, TX -30 dB, 100 attempts per point:

| silence after the frame | fixed window, reference | listen, reference | listen, lead 32 |
|---:|---:|---:|---:|
| 4 frames | 18-20 caught | 97-99 clean | 100 clean |
| 19 frames | 4-8 caught | 94-97 clean | 100 clean |
| 99 frames | 1 caught | 92-94 clean | 100 clean |

Listening does not cost sensitivity. With lead 32 and 19 frames of silence, 100 of 100 frames are
clean from TX -20 to -40 dB and 87-89 at -50 dB, and the cliff is at -55 to -60 dB. The continuous
stream in Lab 11.45 conditions has its cliff at the same place.

## Without hardware

```bash
python tools/run_qpsk_listen_sim.py --json-out listen_sim.json
```

The script runs the receiver RTL in Icarus Verilog on streams built at board B's measured levels
(noise 16 counts rms, a frame peak of about 590 counts for TX -30 dB, a random timing phase per
packet) and prints one table: the fixed window, listen mode without the reference, with the
reference and with lead 32, a weak signal, and a stream of noise only, which checks that a
listening attempt with no packet ends by itself after its 65535-symbol window. With the cases in
parallel it took about half an hour on the course PC.

## Exercises

1. Run step 4 with `--gaps 1` (the frame is on the air half of the time). On the course bench 18-59
   of 100 frames came out gross in listen mode. Why does listening work worse with less silence?
2. Without the decision gate of step 2, how many false locks on noise would you expect over the full
   136 ms window? Take 480 000 symbols per second and the per-bit probability from step 2.
3. The reference symbol is phase state 0, not any other state. What would happen with state 1?
4. Try `--lead 8` and `--lead 16`. What would you measure to decide how long the lead-in has to be,
   and why should the answer depend on the signal level?

<details markdown="1">
<summary>Answers</summary>

1. The detector compares the short mean with the long one, and the long one is supposed to be the
   noise level. When the frame is on the air half of the time, the long mean is half signal, so
   the threshold sits close to the signal level and the detector drops in and out during a packet.
   The loops then freeze in the middle of the frame. A continuous stream in listen mode mostly does
   not lock at all for the same reason. Listen mode is meant for packets with silence between them
   (one frame of signal in five or less worked on the bench); for a continuous stream leave it off.
2. 136 ms is about 65 000 symbols, 130 000 bits. With about 6e-6 per bit that is 0.8 expected false
   locks per window: most long waits would end in garbage.
3. The encoder starts from state 0, so the first frame symbol is `0 + increment`. A reference in
   state 1 makes the receiver decode `increment - 1` for the first symbol. The dibits are Gray
   coded, so that is one wrong bit in every frame: the frame sync still locks, but the one error
   it tolerates is used up, and any noise error in the same 24 bits loses the frame. A reference
   in state 2 would cost two bits and lose every frame.
4. Count gross frames over a run long enough to see a 0.1 % effect (thousands of frames), at
   several TX levels. The loops settle in a number of symbols that depends on the signal-to-noise
   ratio, so a lead-in that is enough at -30 dB may not be at -50 dB. The course bench measured 32
   only; shorter values are untested.

</details>

## Evidence

- [`two-board-burst-20261014.md`](https://github.com/Lay007/zynq-sdr-course/blob/main/reports/hardware/two-board-burst-20261014.md):
  step 1, the fixed window on the board;
- [`qpsk-listen-mode-20261015.md`](https://github.com/Lay007/zynq-sdr-course/blob/main/reports/hardware/qpsk-listen-mode-20261015.md):
  the listen mode, the reference symbol and the lead-in on the board and in simulation, with all
  the runs;
- issue [#68](https://github.com/Lay007/zynq-sdr-course/issues/68).

## What this lab does and does not show

It shows a receiver that waits up to 136 ms for a packet sent once and decodes it as reliably as
a continuous stream, and that the burst format matters as much as the receiver. It does not show a
transmitter that sends a message once: board A still replays a cyclic buffer with silence in it, and
the lead-in exists only in the host-side `burst_iq`. The fabric transmitter and the message tools
of Lab 11.46 do not use it yet. All numbers are from one board pair, one carrier, a conducted path.
