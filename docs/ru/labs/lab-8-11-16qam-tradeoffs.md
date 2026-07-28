# Лабораторная 8.11 — 16-QAM: BER, EVM и ограничения реализации

## Цель

Перейти от QPSK к более высокой спектральной эффективности:

- реализовать Gray mapping/demapping по четыре бита на символ;
- нормировать среднюю мощность и использовать пороги `{-2, 0, +2}/√10`;
- измерить BER/EVM по `Eb/N0`;
- проверить чувствительность к gain/phase imbalance;
- измерить fixed-point quantization и saturation;
- заменить QPSK на 16-QAM в payload-поднесущих OFDM.

```bash
python blocks/block_08_modulation_and_synchronization/python/lab_8_11_16qam_tradeoffs.py
```

Модель сравнивает 200 000 бит на точку. При 52 активных поднесущих QPSK несёт 104 бита на OFDM-символ, а 16-QAM — 208. Плата за удвоение плотности — меньший decision margin и большая чувствительность EVM к дисбалансу и saturation.
