# Block 2 / Блок 2 — Signals, Spectrum, Sampling and I/Q

`block_02_signals_and_sampling` is the signal-interpretation block of the course.
It teaches how to turn a waveform or IQ file into correctly interpreted engineering data.

`block_02_signals_and_sampling` — это блок интерпретации сигналов.
Он учит превращать временную форму или IQ-файл в корректные инженерные данные.

![Block 2 Pipeline](assets/block02_pipeline.svg)

## Main idea / Главная идея

A spectrum can look correct and still lead to a wrong conclusion if `Fs`, `Fc`, IQ order, file format, gain or frequency axis are interpreted incorrectly.

Спектр может выглядеть красиво, но привести к неправильному выводу, если неверно интерпретированы `Fs`, `Fc`, порядок I/Q, формат файла, gain или частотная ось.

## Learning outputs / Результаты блока

| Output | Engineering value |
|---|---|
| Time-domain plot | check amplitude, clipping, DC offset and visible artifacts |
| FFT with correct axis | connect FFT bins to physical/baseband frequency |
| IQ metadata table | make recordings reproducible |
| Aliasing/leakage notes | prevent wrong spectral interpretation |
| Short lab report | document assumptions and interpretation errors |

## Practical path / Практический маршрут

1. Observe a known signal.
2. Define sampling parameters.
3. Build FFT and frequency axis.
4. Interpret I/Q baseband representation.
5. Document metadata.
6. Detect deliberate interpretation mistakes.

## Languages / Языки

- [Русский](README_ru.md)
- [English](README_en.md)

## Connection to next block / Связь со следующим блоком

Block 2 teaches how to read a signal correctly. Block 3 uses this foundation to modify the signal: windowing, filtering, digital mixing, decimation and quality metrics.

Блок 2 учит правильно читать сигнал. Блок 3 использует эту базу для активной обработки: окна, фильтрация, цифровой перенос частоты, decimation и метрики качества.
