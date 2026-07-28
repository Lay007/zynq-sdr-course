# Лабораторная 8.13 — DSSS: захват и processing gain

## Цель

Построить direct-sequence spread-spectrum канал:

- сгенерировать maximal PN sequence длиной 127;
- выполнить spreading/despreading BPSK;
- найти начало по корреляции;
- измерить processing gain против AWGN и narrowband interferer;
- получить BER с количеством сравнённых битов.

```bash
python blocks/block_08_modulation_and_synchronization/python/lab_8_13_dsss_processing_gain.py
```

Код длиной 127 имеет двухуровневую циклическую автокорреляцию и номинальный gain `10·log10(127) ≈ 21 dB`. Корреляция обеспечивает acquisition, а despreading распределяет узкополосную помеху по выходной полосе. Цена — высокая chip rate, полоса и дополнительная PN/correlator-логика.
