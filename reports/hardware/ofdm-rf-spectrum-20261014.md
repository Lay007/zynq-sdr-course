# OFDM transmitter spectrum after a real AD9361 TX, 2026-10-14

## Result

The exact samples of the OFDM RTL transmitter (`ofdm_tx_cp16_path`, random QPSK, 400 symbols,
CP 16) were replayed through board A's DAC and AD9361 transmit chain and recorded with an RTL-SDR.
Compared with the same metric on the digital samples:

| Upper half of the spectrum, dBc against subcarriers 1-26 | Digital samples | RF, DAC at -19 dBFS | RF, DAC at -12 dBFS | RF, DAC at -6 dBFS (0.87 % clipped) |
|---|---:|---:|---:|---:|
| Guard band, subcarriers 28-32 | -18.5 | -22.0 | -21.7 | -21.8 |
| Band edge, subcarriers 31-32 | -19.3 | -24.7 | -24.3 | -24.3 |
| Beyond the digital Nyquist frequency, subcarriers 33-40 | (none) | -21.5 | -21.5 | -21.4 |

- **On RF the guard band is 3-5 dB cleaner than in the digital samples.** The AD9361 transmit
  interpolation filters already roll off near the digital Nyquist frequency. The level is set by
  the rectangular OFDM symbols (Lab 8.14 stage 2g), not by the DAC or the RF chain.
- **The DAC drive level does not change the spectrum** between -19 and -6 dBFS RMS, even with
  0.87 % of the components clipped in the 16-bit domain at -6 dBFS. This agrees with the digital
  back-off sweep in Lab 8.14, where clipping at -6 dBFS moved the guard band by only 0.1 dB.
- **Beyond the digital Nyquist frequency the level stays at -21.5 dBc.** At 2.083 MS/s the lower
  edge of the first image, around the sample rate, starts near subcarrier 38, inside this region.
  This measurement does not separate the image from the continuing sidelobes.

## Setup

| Parameter | Value |
|---|---|
| RF chain | A TX1 -> variable attenuator 0 dB -> 30 dB fixed -> 3-way splitter -> RTL-SDR (other ports: board B RX1, 50 ohm) |
| Board A | vendor image with the DDS/DMA core; TX rate 2.083334 MS/s (read back), LO 915 MHz, RF bandwidth 18 MHz |
| Signal | `tb_ofdm_tx_metrics` output, 400 QPSK symbols (32000 samples) replayed cyclically; native level -18.97 dBFS RMS, steps of +7 and +13 dB in the digital domain |
| Constant RF level | the TX gain is lowered by the same amount as each digital step (-3, -10, -16 dB), so the RTL-SDR sees the same input (-14.2 to -14.5 dBFS, no clipping) |
| RTL-SDR | R820T, 2.4 MS/s (3.2 MS/s returned empty samples on this unit), tuner gain 29.7 dB, tuned 450 kHz above the carrier so the upper half of the signal sits mid-passband; 4 M samples, Welch 2048, Hann |
| Noise | measured with board A silent and subtracted from every PSD; in-band SNR 30.8-31.1 dB (a first run at 5 dB lower level gave the same numbers within 0.3 dB) |
| Script | `tools/measure_ofdm_rf_spectrum.py`; raw metrics and the upper-half PSDs in [`ofdm-rf-spectrum-20261014.json`](ofdm-rf-spectrum-20261014.json) |

## Limits

- Only the upper half of the spectrum is measured, to keep it inside the RTL-SDR's flat passband
  and away from its DC spur. The lower half is assumed symmetric.
- The RTL-SDR is a witness, not a calibrated analyser: levels are relative to the in-band average.
- The modem's own rate (3.84 MS/s) needs a wider receiver than this RTL-SDR to cover the guard band
  and the region beyond Nyquist; this run used the lowest AD9361 rate without FIR instead.
