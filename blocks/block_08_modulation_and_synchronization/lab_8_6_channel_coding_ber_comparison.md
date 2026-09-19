# Lab 8.6 - Channel coding BER comparison with interleaving

## Goal

Compare BER performance for several link variants at the same SNR:

- uncoded baseline;
- convolutional code (hard Viterbi);
- sparse parity-check (LDPC-like) block code;
- with and without interleaving under bursty disturbances.

## Why this lab matters

Everything else in this block fights an impairment *before* the decision. Channel
coding is the complementary tool: add structured redundancy at the transmitter so the
receiver can correct the errors that remain after the best possible synchronization.
The price is bandwidth (a rate-1/2 code doubles the channel bits) and decoder
complexity; the reward is a **coding gain**: the same BER at a lower SNR. Real links
also suffer *bursts* (fades, interferers, a dropped sample), and most decoders are far
better at scattered errors than at runs of them. **Interleaving** spreads a burst over
many codewords so each one sees only a few errors. This lab puts all three ideas on one
plot.

## Executable file

| File | Purpose |
|---|---|
| `blocks/block_08_modulation_and_synchronization/python/lab_8_6_channel_coding_ber_comparison.py` | BER curves across SNR points |

Run from the repository root:

```bash
python blocks/block_08_modulation_and_synchronization/python/lab_8_6_channel_coding_ber_comparison.py
```

## Generated artifacts

```text
docs/assets/lab86_channel_coding_ber.png
docs/assets/lab86_channel_coding_metrics.json
```

## What this lab demonstrates

1. Coding gain relative to uncoded transmission.
2. Impact of burst disturbances on hard-decision decoders.
3. Why interleaving helps under bursty, not purely memoryless, error processes.

## What to expect

The model: BPSK over AWGN plus rare noise bursts (probability 0.012 per start, length 10
bits, burst noise 6x the AWGN level), 80 frames x 240 information bits per SNR point. The
convolutional code is rate 1/2, K = 3, generators (7, 5) octal, with a hard-decision
Viterbi decoder; the "LDPC-like" code is a tiny (36, 24) sparse parity-check code
(rate 2/3) with a bit-flipping decoder (hard decisions; channel reliability only orders the flips). The SNR axis is per transmitted channel
bit, so a coded scheme is *not* given extra energy for its redundancy. The default run
prints:

| SNR | uncoded | conv | conv + interleaver | ldpc-like | ldpc-like + interleaver |
|---:|---:|---:|---:|---:|---:|
| 0 dB | 1.92e-1 | 2.35e-1 | 2.68e-1 | 1.98e-1 | 1.98e-1 |
| 2 dB | 1.39e-1 | 1.20e-1 | 1.45e-1 | 1.39e-1 | 1.43e-1 |
| 4 dB | 9.20e-2 | 6.46e-2 | 5.86e-2 | 8.80e-2 | 8.72e-2 |
| 6 dB | 6.69e-2 | 3.76e-2 | 1.74e-2 | 5.86e-2 | 5.88e-2 |
| 8 dB | 4.33e-2 | 2.87e-2 | 8.39e-3 | 4.45e-2 | 4.67e-2 |

What the numbers say (and what they do not):

- **Coding only pays above a few dB.** At 0 dB the convolutional code is *worse* than
  uncoded (0.235 vs 0.192): too many channel errors overwhelm a hard-decision decoder.
  The crossover here is around 2 dB.
- **Interleaving is the big winner against bursts.** At 6 dB it more than halves the
  convolutional BER (3.8e-2 to 1.7e-2) and at 8 dB cuts it by a factor of about 3.4
  (2.9e-2 to 8.4e-3), because a 10-bit burst that would exceed the code's error-correcting
  ability is now spread across many codewords. Interleaving does *not* help at 0-2 dB,
  where errors are dominated by AWGN, not bursts.
- **The compact LDPC-like code shows essentially no coding gain in this run** (5.9e-2
  vs 6.7e-2 uncoded at 6 dB, and slightly worse at 8 dB). A 36-bit code word with
  hard-decision bit-flipping is too short and too weak to matter; treat it as a
  demonstration of the *structure* (sparse parity checks, iterative decoding), not as
  evidence that LDPC codes do not work. Real LDPC codes use thousands of bits and soft
  (LLR) decoding.
- **Statistical limits.** Each point is about 19 200 information bits, so a BER near
  1e-2 carries a relative uncertainty of roughly 10 %; do not read the small
  differences (for example 1.98e-1 vs 1.97e-1) as real.

## Exercises

1. Set `burst_probability` to 0 and re-run. Does interleaving still help the
   convolutional code? Explain why or why not.
2. Increase `burst_length` from 10 to 30. Which variant degrades first and how does the
   interleaver's benefit change?
3. Compare the coded and uncoded curves at equal *energy per information bit* rather
   than equal energy per channel bit (rate 1/2 costs 3 dB, rate 2/3 about 1.8 dB). Do
   the crossover points move, and by how much?

## Report checklist

- [ ] Include BER curves for all variants.
- [ ] Highlight SNR points where coding gain is most visible.
- [ ] Compare interleaved vs non-interleaved performance.
- [ ] Explain limits of compact LDPC-like and hard-decision decoding model.

