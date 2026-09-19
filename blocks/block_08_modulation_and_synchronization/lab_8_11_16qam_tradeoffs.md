# Lab 8.11 — 16-QAM bridge: BER, EVM and implementation limits

## Goal

Bridge QPSK to higher spectral efficiency with normalized Gray 16-QAM:

- map/demap four bits per symbol with thresholds at `{-2, 0, +2}/√10`;
- measure BER and EVM versus `Eb/N0`;
- expose gain/phase imbalance sensitivity;
- quantify fixed-point quantization and saturation;
- use 16-QAM as an alternative OFDM payload constellation.

## Run

```bash
python blocks/block_08_modulation_and_synchronization/python/lab_8_11_16qam_tradeoffs.py
```

The default sweep compares 200,000 bits per `Eb/N0` point. The OFDM bridge uses 52 active subcarriers: QPSK carries 104 bits per OFDM symbol and 16-QAM carries 208.

## Why this lab matters

QPSK is the workhorse of this course, but links that need more throughput in the same
bandwidth move to higher-order QAM. The trade is simple to state and easy to underestimate:
16-QAM carries 4 bits per symbol instead of 2, but the points are closer together, so every
impairment (noise, gain/phase imbalance, quantization, clipping) eats a larger fraction of the
decision margin. This lab measures that price in three places: against noise, against analog
imbalance, and against fixed-point word length, so you can decide when the extra bit density
is worth having.

## Artifacts

```text
docs/assets/lab811_16qam_ber.png
docs/assets/lab811_16qam_imbalance.png
docs/assets/lab811_16qam_fixed_point.png
docs/assets/lab811_16qam_metrics.json
```

## What to expect

Bit error rate and EVM against `Eb/N0` (200 000 compared bits per point). The last column
is the closed-form Gray-coded 16-QAM approximation
`BER ≈ (3/8)·erfc(sqrt(0.4·Eb/N0))`:

| Eb/N0 | errors | BER | EVM | theory |
|---:|---:|---:|---:|---:|
| 0 dB | 28 371 | 1.42e-1 | 50.1 % | 1.39e-1 |
| 4 dB | 11 749 | 5.87e-2 | 31.6 % | 5.86e-2 |
| 8 dB | 1 825 | 9.13e-3 | 19.9 % | 9.25e-3 |
| 12 dB | 31 | 1.55e-4 | 12.5 % | 1.39e-4 |
| 16 dB | 0 | 0 (< 5e-6) | 7.9 % | 6e-9 |

- **The simulation matches theory** to within Monte Carlo noise, which is what validates the
  Gray mapping and the decision thresholds at `{-2, 0, +2}/sqrt(10)`.
- **BER = 0 at 16 dB means "fewer than about 1 error in 200 000 bits"**, not "error free":
  the theory value is about 6e-9, far below what 200 000 bits can resolve.
- **EVM tracks Eb/N0 smoothly** (50 % → 8 %) while BER falls by orders of magnitude; that is why EVM
  is the better early-warning metric (compare
  [Lab 8.7](/zynq-sdr-course/en/labs/lab-8-7-snr-vs-ber-traps/)).

The imbalance and word-length sweeps are **noiseless**, so what they show is the pure effect of
the impairment, and **BER stays 0 in every row while EVM moves**. Gain/phase imbalance from
(−2 dB, 0°) to (+2 dB, 12°) gives EVM 23.4 %, 11.8 %, 6.2 %, 14.9 %, 26.9 %: the constellation
gets visibly worse long before a decision flips, and there is no noise yet to push the points
across a threshold. For fixed-point, EVM falls from 23.8 % (4 bits) to 11.0 % (6), 8.6 % (8)
and 8.1 % (10 bits) and then stops improving. The reason is in the saturation counter, which reads
50 144 for every word length: the sweep drives the signal at 1.15x, so the outer constellation
levels (0.95 x 1.15 = 1.09) exceed the +1.0 range and are clipped whatever the word length, which
sets an EVM floor near 8 %. BER stays 0 only because a clipped outer point is still on the right side
of its decision threshold, which is exactly why the interpretation below says extra bits cannot
repair clipping caused by insufficient headroom.

## Exercises

1. Find the `Eb/N0` at which 16-QAM reaches BER 1e-3, and the `Eb/N0` at which QPSK does
   (`0.5·erfc(sqrt(Eb/N0))`). How many dB does the doubled bit density cost?
2. In `fixed_point_sweep`, change the drive factor `1.15` to `1.0` and then to `0.9`. The
   saturation counter drops (with drive 1.0 it reaches zero from 8 bits upward) and EVM now
   keeps falling with word length: with drive 1.0 it is about 0.6 % at 8 bits and 0.06 % at
   10 bits. Explain why headroom, not word length, was the limit before.
3. The imbalance sweep is noiseless. Add channel noise at `Eb/N0 = 12 dB` on top of
   the (+1 dB, 8°) imbalance. Does BER stay near the noise-only value of about 1.5e-4?
   Predict first, then run.

## Interpretation

16-QAM doubles payload density relative to QPSK but reduces decision margin. EVM therefore exposes gain/phase imbalance and numeric saturation before BER necessarily becomes large. Increasing word length reduces quantization error, while extra bits cannot repair clipping caused by insufficient headroom.
