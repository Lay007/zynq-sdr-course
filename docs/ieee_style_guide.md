# IEEE-style Engineering Presentation Guide

This guide defines the visual and reporting style for the SDR course materials, GitHub demos, laboratory reports, and future article-ready figures.

## Goals

The course should look like an engineering research project:

- clear block diagrams;
- reproducible plots;
- explicit experiment parameters;
- quantitative metrics;
- concise conclusions;
- consistent terminology.

## Figure style

Recommended figure properties:

| Property | Recommendation |
|---|---|
| Background | white |
| Font | readable sans-serif for GitHub, serif acceptable for PDF |
| Line width | medium, not thin |
| Grid | light grid for plots |
| Axes | labeled with units |
| Legends | outside the data region if possible |
| Captions | short, technical and meaningful |

## Plot naming convention

Use predictable names:

```text
lab01_tone_fft.png
lab02_am_spectrum.png
lab02_fm_spectrum.png
lab03_qpsk_constellation.png
lab04_cfo_before_after.png
lab05_impairments_evm.png
lab06_end_to_end_ber.png
```

## Recommended plot set per lab

### Lab 1 — tone
- time-domain IQ preview;
- FFT spectrum;
- HDSDR screenshot;
- peak-frequency estimate.

### Lab 2 — AM/FM
- AM spectrum;
- FM spectrum;
- recovered message;
- occupied bandwidth estimate.

### Lab 3 — BPSK/QPSK
- constellation diagram;
- pulse-shaped waveform;
- spectrum;
- BER summary.

### Lab 4 — synchronization
- constellation before CFO correction;
- constellation after CFO correction;
- timing recovery result;
- BER before/after synchronization.

### Lab 5 — impairments
- clean signal baseline;
- noisy constellation;
- clipped spectrum;
- EVM/BER comparison.

### Lab 6 — end-to-end
- full-chain diagram;
- received spectrum;
- final constellation;
- metrics table.

## IEEE-style report structure

Use this structure for laboratory reports:

```text
Title
Abstract
I. Introduction
II. Experimental Setup
III. Signal Model
IV. Implementation
V. Measurement Results
VI. Discussion
VII. Conclusion
References
Appendix
```

## Metric table format

| Metric | Value | Unit | Comment |
|---|---:|---|---|
| Fs | 2.4 | MS/s | receiver sampling rate |
| Fc | 915 | MHz | carrier frequency |
| SNR | 32.1 | dB | estimated from FFT |
| EVM | 4.8 | % | QPSK constellation |
| BER | 1.2e-4 | - | after synchronization |

## GitHub visual style

For README and demo pages:

- prefer vertical Mermaid diagrams for readability;
- keep diagrams light, not dark;
- use concise captions;
- show one key visual per lab;
- keep demo sections short and visual.

## Engineering rule

Every plot should answer one engineering question.

Examples:

- Is the tone at the expected frequency?
- Is the receiver overloaded?
- Did synchronization improve BER?
- Does fixed-point conversion introduce unacceptable error?
