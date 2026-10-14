# Sampling phase and the eye opening on silicon, 2026-10-14

Board B, image `8fb3a6a5` (#65), PL fabric loopback (no RF, no noise). The receiver samples one
value per symbol at a fixed `start_offset`, 8 samples per symbol, no timing recovery. The sweep
moves `start_offset` from 40 to 80 in steps of 1, three bursts per point. Raw data:
[`bpsk-qpsk-sampling-phase-silicon-20261014.json`](bpsk-qpsk-sampling-phase-silicon-20261014.json)
(per point: `[received, total errors, rotation]` for each burst).

All three bursts gave identical results at every point: in the fabric loopback the result depends
only on the sampling phase.

## BPSK, 281-bit frame, exact preamble lock

| Offset | 40-42 | 43 | 44 | 45 | 46-50 | 51 | 52 | 53 | 54-58 | 59 | 60 | 61 | 62-66 | 67 | 68 | 69-80 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Received / errors | 278/0 | 278/17 | 278/67 | 279/13 | 279/0 | 279/17 | 279/67 | 280/13 | 280/0 | 280/17 | 280/67 | 281/13 | 281/0 | 281/17 | 281/67 | 270-271 / 125-133 |

The pattern repeats every 8 samples, one symbol. Taking the clean runs as the eye centre (48, 56,
64), five phases out of eight decode without errors (centre +-2 samples), and the three phases
around the symbol boundary fail:

| Distance from the eye centre | Silicon | Lab 5.8 simulation |
|---|---:|---:|
| +-1, +-2 samples | 0 | 0 |
| -3 samples | 13 | 12 |
| +3 samples | 17 | 16 |
| 4 samples (half a symbol) | 67 | 68 (+4), 72 (-4) |

The silicon numbers match the Lab 5.8 exercise 2 simulation to within one bit. The same RRC
pulse and fixed sampler give the same eye on the board.

`received` grows by one bit every 8 samples between 40 and 68: a later start leaves fewer extra
bits before the frame, and the burst window ends at a fixed time. From 69 the sampler starts after
the beginning of the preamble; the counter then locks on a matching pattern inside the data and
reports about 130 errors (the random-data false lock of Lab 5.10 exercise 3).

## QPSK, 140-symbol frame

| Offset | 40-42 | 43-45 | 46-50 | 51-53 | 54-58 | 59-61 | 62-66 | 67-80 |
|---|---|---|---|---|---|---|---|---|
| Received / errors | 140/0 | 0/0 | 140/0 | 0/0 | 140/0 | 0/0 | 140/0 | 0/0 |

The clean phases are the same as for BPSK. At the three bad phases the QPSK counter does not lock
at all and reports nothing received, where the BPSK counter locks and reports errors. Assumed, not
checked in this run: the preamble errors at those phases exceed the QPSK lock tolerance. From 67
the preamble start is missed and the QPSK counter does not lock either, so it shows no false lock
in this range.

## What it means

- This is the expected behaviour of a fixed-phase sampler, not a defect: the eye is open for
  5/8 of a symbol. The `start_offset` sweep in the Block 11 flow picks a point in that window.
- For teaching, the board reproduces the Lab 5.8 eye measurement exactly, and it shows the
  difference between a counter that locks and counts errors (BPSK) and one that refuses to lock
  (QPSK). A BER figure is only meaningful together with the number of frames that locked.
