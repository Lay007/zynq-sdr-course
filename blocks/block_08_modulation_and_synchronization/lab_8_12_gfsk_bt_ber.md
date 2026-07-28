# Lab 8.12 — GFSK: BT, occupied bandwidth and discriminator BER

## Goal

Build a continuous-phase GFSK link and study:

- Gaussian pulse shaping and the `BT` bandwidth/time trade-off;
- constant-envelope transmission and approximately `0 dB` PAPR;
- quadrature-discriminator decisions;
- occupied bandwidth and BER versus `Eb/N0`;
- differences from OFDM peak back-off and CSS processing gain.

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

## Interpretation

Lower `BT` narrows the occupied spectrum but spreads transitions across more neighbouring symbols. GFSK keeps a constant envelope and is friendly to nonlinear transmitters, unlike OFDM, but its simple discriminator receiver pays a sensitivity penalty. The BER curve therefore reports actual decisions rather than inferring link quality from spectrum alone.
