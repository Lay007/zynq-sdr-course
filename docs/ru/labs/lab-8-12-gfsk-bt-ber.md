# Лабораторная 8.12 — GFSK: BT, полоса и BER

## Цель

Построить continuous-phase GFSK-канал и исследовать:

- Gaussian pulse shaping и компромисс `BT`;
- constant envelope и PAPR около `0 dB`;
- quadrature/discriminator receiver;
- occupied bandwidth и BER по `Eb/N0`;
- отличие от OFDM back-off и CSS processing gain.

```bash
python blocks/block_08_modulation_and_synchronization/python/lab_8_12_gfsk_bt_ber.py
```

Меньший `BT` сужает спектр, но растягивает переходы на соседние символы. GFSK удобен для нелинейного передатчика благодаря постоянной огибающей, однако простой discriminator receiver уступает когерентным схемам по чувствительности. Поэтому лабораторная измеряет решения BER, а не ограничивается спектром.
