# Block 2. Signals, Spectrum, Sampling, and I/Q

## Purpose

Block 2 transforms the first received signal from Block 1 into engineering-grade data. The goal is to correctly interpret time-domain signals, spectra, frequency axes and IQ recordings.

![Block 2 Pipeline](assets/block02_pipeline.svg)

## Why this block matters

If sampling rate, center frequency or IQ format are wrong, the spectrum may look correct visually but lead to incorrect engineering conclusions. This block introduces disciplined SDR data interpretation.

Core idea:

```text
signal -> sampling -> FFT -> I/Q -> metadata -> interpretation check
```

## Learning outcomes

After completing this block, the student can:

- distinguish RF frequency from baseband frequency;
- build a correct FFT frequency axis;
- relate sample rate, FFT size and resolution;
- explain aliasing and mirrored spectrum;
- detect DC offset, clipping and spectral leakage;
- document IQ recordings for reproducibility.

## Topics

| Topic | Engineering meaning |
|---|---|
| Time-domain signal | amplitude, shape, spikes, clipping, DC offset |
| Sampling | `Fs`, Nyquist, aliasing, time step |
| FFT | bins, resolution bandwidth, windowing, leakage |
| I/Q | complex baseband, positive and negative frequencies |
| Metadata | `Fs`, `Fc`, gain, format, I/Q order, duration |
| Validation | deliberate interpretation mistakes and diagnostics |

## Lab path

| Step | Task | Check |
|---:|---|---|
| 1 | plot time-domain waveform | amplitude, DC, clipping |
| 2 | plot FFT | correct frequency axis |
| 3 | change `Fs` | frequency interpretation error |
| 4 | change `Fc` | baseband-to-RF mapping |
| 5 | swap/sign-change I/Q | mirrored spectrum |
| 6 | write metadata table | reproducibility |

## Practical work

The student takes a known tone, builds time and frequency plots, and then intentionally changes Fs/Fc or metadata to observe incorrect interpretations.

## Engineering result

Outputs of the block:

- time-domain waveform;
- FFT with correct frequency axis;
- parameter table;
- short report describing interpretation errors.

## Connection to Block 3

Block 2 answers: **what exactly do we see in the signal?**

Block 3 answers the next question: **how do we modify, filter, shift and prepare this signal for FPGA implementation?**
