# Lab 8.12 — GFSK: BT, occupied bandwidth and discriminator BER

## Goal

Build a continuous-phase GFSK link and study:

- Gaussian pulse shaping and the `BT` bandwidth/time trade-off;
- constant-envelope transmission and approximately `0 dB` PAPR;
- quadrature-discriminator decisions;
- occupied bandwidth and BER versus `Eb/N0`;
- differences from OFDM peak back-off and CSS processing gain.

## Why this lab matters

Not every radio can afford a linear power amplifier. GFSK (the modulation behind Bluetooth
and many low-power sub-GHz links) keeps a **constant envelope**, so a cheap, efficient,
nonlinear amplifier can transmit it without spectral regrowth. The price is paid in two
places that this lab measures: the Gaussian filter's `BT` product trades occupied bandwidth
against inter-symbol interference (ISI), and the simple discriminator receiver is far less
sensitive than a coherent one.

## Run

```bash
python blocks/block_08_modulation_and_synchronization/python/lab_8_12_gfsk_bt_ber.py
```

## Artifacts

```text
docs/assets/lab812_gfsk_bt_waveforms.png
docs/assets/lab812_gfsk_bandwidth.png
docs/assets/lab812_gfsk_ber.png
docs/assets/lab812_gfsk_metrics.json
```

## What to expect

`BT` sets the 99 % occupied bandwidth (normalised to the symbol rate): 0.079 at BT = 0.3,
0.099 at BT = 0.5 and 0.123 at BT = 1.0. The constant-envelope error is at floating-point noise
level (2e-16) and the PAPR is 0 dB for every BT, which is the whole point of the modulation.

The BER sweep (BT = 0.5, about 40 000 bits per point) reads:

| Eb/N0 | BER |
|---:|---:|
| 0 dB | 0.466 |
| 8 dB | 0.330 |
| 16 dB | 0.130 |
| 24 dB | 0.080 |
| 32 dB | 0.034 |
| 40 dB | 0.0084 |

Read this curve for what it is:

- **It needs an absurd 40 dB to reach 1 %.** A good GFSK receiver reaches that at roughly 10-12 dB.
  This lab's receiver has *no channel filter*: it sums raw per-sample phase differences over
  each symbol, so it integrates the noise of the whole sample-rate bandwidth, and it decides
  from a symbol-aligned sum that leaves very little margin for worst-case ISI patterns. The curve
  shows the *trend* (BER falls as Eb/N0 rises) and the relative cost of this receiver, not
  the performance a real GFSK link achieves.
- **ISI is visible without any noise.** With no noise at all this discriminator makes no errors at
  BT = 0.5 or 1.0, but at BT = 0.3 it already decides about 20 % of the bits wrongly. The
  narrow filter smears each symbol into its neighbours so much that this simple detector cannot
  recover them; real receivers use a matched (Gaussian) receive filter or sequence detection
  for low `BT`.
- **The BER ends at zero only around 60 dB** in a quick check, because worst-case bit patterns leave
  a small decision margin; that is a property of this detector, not of GFSK.

## Exercises

1. Reproduce the noiseless result: run `discriminator_demodulate` on a noiseless waveform for
   BT = 0.3, 0.5 and 1.0. What BER do you get, and what does that say about the choice of `BT`?
2. Add a moving-average (symbol-length) filter to the received waveform before the
   discriminator. How much does the Eb/N0 needed for BER 1e-2 fall?
3. Compare the occupied bandwidth against BT. Where is the knee, and how does it
   relate to the ISI you measured in exercise 1?

## Interpretation

Lower `BT` narrows the occupied spectrum but spreads transitions across more neighbouring symbols. GFSK keeps a constant envelope and is friendly to nonlinear transmitters, unlike OFDM, but its simple discriminator receiver pays a sensitivity penalty. The BER curve therefore reports actual decisions rather than inferring link quality from spectrum alone.
