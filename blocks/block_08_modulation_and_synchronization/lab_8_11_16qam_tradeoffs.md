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

## Artifacts

```text
docs/assets/lab811_16qam_ber.png
docs/assets/lab811_16qam_imbalance.png
docs/assets/lab811_16qam_fixed_point.png
docs/assets/lab811_16qam_metrics.json
```

## Interpretation

16-QAM doubles payload density relative to QPSK but reduces decision margin. EVM therefore exposes gain/phase imbalance and numeric saturation before BER necessarily becomes large. Increasing word length reduces quantization error, while extra bits cannot repair clipping caused by insufficient headroom.
