# OFDM through a radio channel: frame synchronization and the RTL receiver (#48, stage 4, simulation)

Issue #48 has reached verification stage 3: the modem `ofdm_axi_modem` ran on board A behind an AXI
DMA, 3 072 000 bits without an error
([ofdm-dma-fabric-loopback-20261014.md](../hardware/ofdm-dma-fabric-loopback-20261014.md)). Stage 4
puts a radio between the transmitter and the receiver. The receiver of the modem, however, takes
symbols that are already cut, 80 samples each with `tlast` on the 80th; nothing in it finds a frame
in a continuous stream. This report adds that missing piece outside the modem and checks it, with
the exact RTL receiver, in simulation. **No hardware was involved.** Raw data:
[`ofdm-rf-link-sync-sim-20261019.json`](ofdm-rf-link-sync-sim-20261019.json).

## The frame and the synchronization

```text
silence | sync preamble: CP 16 + 64 samples made of two equal halves | training symbol | data | silence
```

The training and data symbols are the RTL transmitter's own output
(`tb_ofdm_modem_file.sv`, MODE = 0, the modem with the parameters of the stage-3 bitstream). The
preamble (Schmidl and Cox) carries QPSK on the even used subcarriers only, so its 64-sample body is
two equal halves; it is only for finding the frame and never reaches the modem.

`tools/ofdm_rf_link.py` computes the metric M(d) = |P(d)|^2 / R(d)^2, where P correlates the two
32-sample halves and R is the mean energy of **both** halves. The textbook form normalizes by the
second half only; on the first simulated frame its peak (594) sat at the end of the burst, where the
second half falls into silence and R goes to the noise floor. With both halves M stays at or below
1. The plateau of M is as long as the cyclic prefix; its centre gives the start of the preamble
body, the first training symbol starts 64 samples later, and the receiver window is put 4 samples
earlier, inside the cyclic prefix: an early window only adds a phase slope across the subcarriers,
which the channel equalizer removes, while a late one would mix two symbols. The aligned symbols go
to the RTL receiver (`tb_ofdm_modem_file.sv`, MODE = 1), which trains its equalizer on the training
symbol and decides the data.

## Results

Channel per frame: a random lead of 300-900 samples, a random carrier phase, white noise at the
given SNR over the occupied band, 12-bit quantization; "fractional" adds a random fractional delay.
5 frames of 10 data symbols per case (4800 bits), the modem rate taken as 2.083 MS/s:

| case | frame start error (samples) | bit errors / 4800 |
|---|---|---:|
| SNR 35 dB, fractional delay | -1 ... 0 | 0 |
| CFO 3 kHz, SNR 25 dB | -1 ... 0 | 0 |
| CFO 10 kHz | -1 ... 0 | 0 |
| CFO 15 kHz | -1 ... 0 | 0 |
| CFO 20 kHz | -1 ... 0 | 2378 |
| board-like: CFO 3 kHz, DC 5 % of RMS, I/Q 0.3 dB / 2 deg | -1 ... 0 | 0 |
| SNR 20 dB | -1 ... 0 | 0 |
| SNR 15 dB | -1 ... +1 | 0 |
| SNR 10 dB | 0 ... +1 | 2 |

The frame is found within one sample in every case. The modem's own CFO corrector (cyclic-prefix
correlation) covers +-half a subcarrier spacing, +-16.3 kHz at this rate; 20 kHz is beyond it and
fails, as expected. The preamble already gives a CFO estimate over +-one spacing (3886 Hz for a
true 4000 Hz in the capture check below), so a coarse correction before the modem would double the
range if a board pair ever needs it. The course boards differ by a few kHz.

## The recording path

For the bench, `--save-tx` writes one frame as int16 I/Q for `iio_writedev` (7 dB above the RTL
output, -12 dBFS RMS, the clip-free level measured on Oct 13), and `--rx-capture` decodes an
`iio_readdev` recording. Checked by emulation: the saved frame played three times cyclically, the
recording starting 1234 samples into the first frame, SNR 25 dB, CFO 4 kHz, fractional delay 0.37,
DC and I/Q imbalance, 12-bit integers. The first complete frame was found exactly where it starts
(sample 1972), the CFO estimate was 3886 Hz, and 1920 of 1920 bits were right.

`tools/run_ofdm_rf_link_board.py` does the same with two boards: one plays the frame, the other
records, the PC decodes. It has not been run yet (the bench was taken apart); it is the first thing
for the next bench session.

## Limits

- Simulation only. The channel model has no multipath, no phase noise and no sampling-clock offset
  between the boards; a recording will show what it misses.
- The received level is normalized in software before the RTL receiver (a stand-in for an AGC);
  stage 4b, with the modem in the radio image, needs that in the fabric.
- 5 frames per case; the BER at 10 dB SNR (2 of 4800) is one sample of a tail, not a curve.
