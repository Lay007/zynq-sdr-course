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

`BT` sets the 99 % occupied bandwidth (as a fraction of the sample rate, 8 samples per symbol): 0.079 at BT = 0.3,
0.099 at BT = 0.5 and 0.123 at BT = 1.0, i.e. 0.63, 0.79 and 0.98 of the symbol rate. The constant-envelope error is at floating-point noise
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
   discriminator. Does the Eb/N0 needed for BER 1e-2 fall? Try 2, 4 and 8 samples.
3. Compare the occupied bandwidth against BT. Where is the knee, and how does it
   relate to the ISI you measured in exercise 1?

<details markdown="1">
<summary>Answers (checked by running the lab script)</summary>

1. Over 20 000 bits: BER 0.199 at BT = 0.3, and 0 at BT = 0.5 and 1.0 (0.187 at BT = 0.4, 0.280 at BT = 0.2). Below BT ≈ 0.5 the Gaussian filter spreads each symbol so far into its neighbours that this detector errs without any noise. `BT` is a bandwidth knob with a cliff behind it for a simple receiver.
2. No. A symbol-length (8-sample) average lowers the BER at low Eb/N0 (0.33 → 0.15 at 8 dB) but adds its own ISI, which creates a floor near 0.1, so 1e-2 is never reached; 2–3 samples leave the 1e-2 point at 40–42 dB, and from 5 samples errors appear even without noise. The reason is the detector: the sum of the phase differences over a symbol telescopes to the phase difference between its first and last samples, so it averages nothing, and its errors come from a few bit patterns with very little margin. A filter long enough to cut noise also shrinks that margin. A real fix is a matched Gaussian receive filter with a decision at the symbol centre, or sequence detection.
3. The 99 % bandwidth grows smoothly with BT: 0.066, 0.079, 0.090, 0.098, 0.111 and 0.123 of the sample rate for BT = 0.2, 0.3, 0.4, 0.5, 0.7 and 1.0 (×8 for the symbol rate: 0.53 to 0.98). The knee is not in the bandwidth but in the ISI of exercise 1, which jumps between BT = 0.4 and 0.5. Going from 0.5 to 0.3 saves only about 20 % of bandwidth and costs 20 % bit errors, which is why standards that use BT = 0.3 pair it with better receivers.

</details>

## Interpretation

Lower `BT` narrows the occupied spectrum but spreads transitions across more neighbouring symbols. GFSK keeps a constant envelope and is friendly to nonlinear transmitters, unlike OFDM, but its simple discriminator receiver pays a sensitivity penalty. The BER curve therefore reports actual decisions rather than inferring link quality from spectrum alone.
