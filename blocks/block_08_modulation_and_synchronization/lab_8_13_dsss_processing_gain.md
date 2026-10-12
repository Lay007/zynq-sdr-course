# Lab 8.13 — DSSS acquisition and processing gain

## Goal

Build a direct-sequence spread-spectrum link:

- generate a length-127 maximal PN sequence;
- spread and despread BPSK data;
- acquire packet timing by correlation;
- measure processing gain against AWGN and a narrowband tone interferer;
- report BER with compared-bit counts.

## Why this lab matters

Direct-sequence spread spectrum multiplies each data bit by a fast pseudo-random chip
sequence. The result occupies a much wider band at a much lower power density, which buys
three things: resistance to narrowband interference, the ability to work below the noise
floor (the receiver correlates against the known code), and precise timing from the
correlation peak. It is the basis of GPS, CDMA and 802.11b, and the same idea, applied to chirps,
is the LoRa/CSS of Lab 8.20-8.22. Here you build the mechanism and measure what it does and, just
as importantly, what it does not do.

## Run

```bash
python blocks/block_08_modulation_and_synchronization/python/lab_8_13_dsss_processing_gain.py
```

## Artifacts

```text
docs/assets/lab813_dsss_autocorrelation.png
docs/assets/lab813_dsss_acquisition.png
docs/assets/lab813_dsss_ber.png
docs/assets/lab813_dsss_metrics.json
```

## What to expect

With a 127-chip m-sequence (7-bit LFSR):

| Quantity | Value |
|---|---|
| Nominal processing gain `10·log10(127)` | 21.04 dB |
| Largest off-peak autocorrelation | 0.0079 (= 1/127) |
| Acquisition (at −8 dB SNR) | detected start 73, true start 73, error 0 chips |
| Narrowband interferer suppression | 38.2 dB (interferer at +10 dB J/S) |

BER against `Eb/N0` (20 000 bits per point):

| Eb/N0 | BER, AWGN only | BER, with +10 dB J/S tone |
|---:|---:|---:|
| −6 dB | 0.240 | 0.244 |
| −3 dB | 0.154 | 0.159 |
| 0 dB | 0.079 | 0.077 |
| 3 dB | 0.0249 | 0.0246 |
| 6 dB | 0.0030 | 0.0027 |
| 9 dB | 0 | 5e-5 (1 error) |

The important reading is what is *not* there:

- **The AWGN column is ordinary BPSK.** The theory values are 0.079 at 0 dB and 0.0024 at 6 dB,
  and the lab matches them. Spreading gives **no BER gain in pure white noise**: spreading
  the signal spreads the noise it must beat too. The 21 dB "processing gain" is not a
  sensitivity improvement in AWGN.
- **The gain shows up against interference.** A tone 10 dB stronger than the signal
  changes BER by no more than Monte Carlo noise: the despreader spreads the tone across the
  full bandwidth while the wanted bit collapses to a single value, and the measured suppression is
  38 dB, which is more than the nominal 21 dB; how much more depends on where the tone sits
  relative to the spectrum of the code.
- **Acquisition works at −8 dB SNR**, where a sample-by-sample look at the waveform sees
  only noise: the correlation peak (gain of 127) rises clearly above the 1/127 sidelobes.
- **The price** is bandwidth: this signal occupies 127 times the bandwidth of the data.

## Exercises

1. Increase the interferer to `J/S = 30 dB`. At what level does the BER start to rise, and how does
   that compare with the 21 dB processing gain?
2. Replace the 127-chip code with a 31-chip one (5-bit LFSR). What happens to the processing gain,
   the off-peak autocorrelation and the acquisition reliability?
3. Delay the local code by one chip and measure BER. What does that tell you about why acquisition is
   necessary at all?

<details markdown="1">
<summary>Answers (checked by running the lab script)</summary>

1. At Eb/N0 = 9 dB the BER stays at 0 up to J/S = 20 dB, then rises: 5e-5 at 22 dB, 1e-4 at 25 dB and 1.6e-3 at 30 dB. That is the order of the 21 dB processing gain: once the interferer exceeds the signal by more than the gain, what is left after despreading is comparable to the noise. For this particular tone frequency the despreading suppression is even 38 dB, which is why the BER rises gently rather than abruptly.
2. The processing gain drops from 21.0 to 14.9 dB (`10·log10(31)`), and the suppression of the same tone from 38.2 to 11.2 dB. The off-peak periodic autocorrelation of both m-sequences is 1 in magnitude, i.e. −29.8 dB relative to the peak for 31 chips against −42 dB for 127. Acquisition at −8 dB SNR, over 200 trials, succeeds 188 times with 31 chips and 200 times with 127: a shorter code collects less energy per correlation.
3. BER 0.51: a code shifted by one chip is almost uncorrelated with itself (the off-peak value is −1/127), so despreading returns noise. Spreading gain exists only when the local code is aligned to within a fraction of a chip, which is exactly what acquisition provides before any data can be read.

</details>

## Interpretation

The 127-chip code has an ideal two-level cyclic autocorrelation and nominal processing gain `10·log10(127) ≈ 21 dB`. Correlation supplies acquisition timing, while despreading distributes a narrowband interferer across the output bandwidth. This robustness costs chip rate, bandwidth and correlator/PN synchronization logic.
