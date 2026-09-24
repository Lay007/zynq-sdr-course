# Lab 8.21 — CSS dechirp and FFT detector

## Goal

Turn the waveform from Lab 8.20 into a reproducible symbol detector and quantify its limits:

- build a complete symbol bank for the selected spreading factor;
- derive the noiseless symbol-to-FFT-bin mapping;
- detect random symbols after dechirping;
- measure symbol error rate (SER) versus SNR;
- measure sensitivity to carrier-frequency offset (CFO);
- report peak-to-second-peak separation as a detector confidence metric.

## Detector structure

```mermaid
flowchart LR
    RX[received CSS symbol] --> MIX[dechirp with conjugate reference]
    REF[reference upchirp] --> MIX
    MIX --> FFT[FFT]
    FFT --> ARGMAX[maximum-magnitude bin]
    ARGMAX --> MAP[inverse bin-to-symbol mapping]
    MAP --> OUT[detected symbol]
```

## Run

```bash
python blocks/block_08_modulation_and_synchronization/python/lab_8_21_css_dechirp_fft.py
```

## Generated artifacts

```text
docs/assets/lab821_css_ser_vs_snr.png
docs/assets/lab821_css_ser_vs_cfo.png
docs/assets/lab821_css_example_fft.png
docs/assets/lab821_css_detector_metrics.json
```

## Default experiment

- spreading factor: `SF=7`;
- bandwidth: `125 kHz`;
- 800 random symbols per sweep point;
- SNR sweep: `-18 ... 0 dB`;
- normalized CFO sweep: `-0.45 ... +0.45` FFT-bin spacings.

The normalized CFO axis is useful because one FFT-bin spacing equals `BW / 2^SF`. It makes the experiment portable across bandwidth and spreading-factor choices.

## Acceptance criteria

The executable lab checks or exposes enough data to verify that:

- the noiseless symbol-to-bin mapping is a permutation;
- the example symbol is detected correctly;
- SER at 0 dB is zero for the deterministic default seed;
- the lowest-SNR point has a clearly nonzero SER;
- fractional-bin CFO degrades the detector before the FFT peak crosses into a neighbouring bin.

## Why SER, not only SNR

A spectrum or SNR estimate does not prove that a digital link works. This lab therefore reports the actual symbol decisions. The same principle should later be extended to BER, packet error rate (PER), missed detections and false alarms.

## Follow-on work

The next packet-level CSS laboratory should add:

- a repeated-chirp preamble;
- packet-start detection;
- coarse and fine CFO estimation;
- sample-rate offset;
- sync-word and downchirp handling;
- BER/PER and false-alarm measurements.

## What to expect

SER against SNR (800 symbols per point, `SF = 7`):

| SNR | −18 dB | −15 dB | −12 dB | −9 dB | −6 dB | −3 dB | 0 dB |
|---|---:|---:|---:|---:|---:|---:|---:|
| SER | 0.853 | 0.636 | 0.245 | 0.010 | 0 | 0 | 0 |

SER against normalized CFO (fraction of one bin spacing):

| CFO | −0.45 | −0.30 | −0.15 | 0 | +0.15 | +0.30 | +0.45 |
|---|---:|---:|---:|---:|---:|---:|---:|
| SER | 0.405 | 0.078 | 0.015 | 0.011 | 0.019 | 0.080 | 0.431 |

- **The detector works below the noise floor** (SER 1 % at −9 dB SNR): dechirping and a 128-point FFT
  collect the whole symbol's energy into one bin, a processing gain of `10*log10(128) = 21 dB`.
- **Half a bin of CFO nearly destroys it**: at ±0.45 bin the energy splits between two bins and SER
  exceeds 40 %. This is why Lab 8.22 estimates and removes CFO before payload decisions.

## Exercises

1. Repeat the SNR sweep with `SF = 9`. By how many dB does the curve move, and does it match
   `10*log10(512/128)`?
2. At what CFO (in hertz) does a 125 kHz, `SF = 7` link lose half a bin? Compare with a 0.3 ppm
   oscillator offset at 868 MHz.

## Report checklist

- [ ] Include the SER-versus-SNR curve.
- [ ] Include the normalized-CFO sensitivity curve.
- [ ] Include one dechirped FFT example.
- [ ] State the number of compared symbols at every point.
- [ ] Explain why peak-to-second-peak ratio is useful but does not replace SER/PER.
