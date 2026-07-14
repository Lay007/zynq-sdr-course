# Lab 8.10 — OFDM PAPR, clipping and spectral regrowth

## Goal

Extend the OFDM mini-link with a transmitter-focused experiment that connects waveform statistics to real RF and fixed-point constraints:

- estimate the OFDM peak-to-average power ratio (PAPR) distribution;
- plot the complementary cumulative distribution function (CCDF);
- apply magnitude clipping at several `A/RMS` ratios;
- measure the resulting PAPR, EVM, BER and out-of-band energy;
- explain why digital back-off and peak dBFS matter before the AD9363 transmit path.

## Why this lab matters

A QPSK constellation can look robust while the time-domain OFDM waveform still contains large peaks. Those peaks can cause fixed-point overflow, DAC clipping or RF power-amplifier compression. Reducing PAPR by hard clipping lowers the peaks, but it also increases EVM and spectral regrowth and can eventually create bit errors.

## Processing chain

```mermaid
flowchart LR
    BITS[random bits] --> MAP[QPSK mapper]
    MAP --> ALLOC[subcarrier allocation]
    ALLOC --> IFFT[oversampled IFFT]
    IFFT --> CLIP[magnitude clipping]
    CLIP --> AWGN[AWGN]
    AWGN --> FFT[FFT]
    FFT --> METRICS[PAPR / EVM / BER / OOB]
```

## Run

```bash
python blocks/block_08_modulation_and_synchronization/python/lab_8_10_ofdm_papr_clipping.py
```

## Generated artifacts

```text
docs/assets/lab810_ofdm_papr_ccdf.png
docs/assets/lab810_ofdm_clipping_tradeoff.png
docs/assets/lab810_ofdm_spectral_regrowth.png
docs/assets/lab810_ofdm_papr_metrics.json
```

## Default experiment

- `FFT=64`;
- 52 occupied subcarriers;
- 4× oversampling for PAPR estimation;
- 4000 OFDM symbols for the CCDF;
- 300 OFDM symbols and 31,200 compared bits per clipping point;
- SNR = 24 dB;
- clipping ratios from `3.0` down to `0.7` times RMS amplitude.

With the deterministic default seed, the unclipped signal has roughly 7 dB median PAPR and about 10 dB at the 99th percentile. Severe clipping reduces average PAPR to about 1 dB, but raises EVM above 25%, increases out-of-band energy and produces nonzero BER.

## Metrics and interpretation

- **PAPR** describes peak stress on the digital and RF path.
- **EVM** exposes in-band constellation distortion before BER necessarily changes.
- **BER** proves whether the digital decisions still work.
- **Out-of-band/in-band power** is a compact spectral-regrowth indicator; it is not a standards-compliant ACLR measurement.

This combination reinforces a key course rule: no single metric is sufficient. A waveform can have BER=0 while EVM and spectral quality are already degrading.

## Report checklist

- [ ] Include the PAPR CCDF.
- [ ] Report median and 99th-percentile PAPR.
- [ ] Compare unclipped and clipped EVM.
- [ ] Report BER with the number of compared bits.
- [ ] Include the spectral-regrowth plot.
- [ ] Recommend a safe digital back-off strategy for a future AD9363 measurement.
