# Block 3 / Блок 3 — DSP Basics

`block_03_dsp_basics` is the active signal-processing block of the course.
It moves from interpreting IQ data to transforming it with FFT windows, filters, digital mixing, multirate operations and metrics.

`block_03_dsp_basics` — это блок активной DSP-обработки.
Он переводит студента от интерпретации IQ-данных к их изменению с помощью FFT-окон, фильтров, цифрового переноса частоты, multirate-операций и метрик.

![Block 3 Pipeline](assets/block03_pipeline.svg)

## Main idea / Главная идея

A DSP chain is engineering-ready only when every operation is measurable, reproducible and explainable in terms of spectrum, delay, noise, distortion and future FPGA implementation cost.

DSP-цепочка становится инженерной только тогда, когда каждая операция измерима, воспроизводима и объяснима через спектр, задержку, шум, искажения и будущую цену FPGA-реализации.

## Lab matrix / Матрица лабораторных

| Lab | Topic | Main artifact | FPGA/RF connection |
|---|---|---|---|
| Lab 3.1 | FFT windows and leakage | spectrum comparison | measurement discipline |
| Lab 3.2 | FIR low-pass filtering | response + filtered IQ | future FIR RTL block |
| Lab 3.3 | Digital mixing | spectrum before/after shift | NCO + complex multiplier |
| Lab 3.4 | Decimation | anti-aliasing validation | rate-change block for FPGA |

## Engineering outputs / Инженерные результаты

- windowed FFT plots;
- FIR response and filtered spectrum;
- digital mixing before/after plots;
- decimation with anti-aliasing evidence;
- SNR/noise-floor/spur observations;
- short reproducible report for each lab.

## Languages / Языки

- [Русский](README_ru.md)
- [English](README_en.md)

## Connection to next blocks / Связь со следующими блоками

Block 3 prepares the DSP primitives that later become fixed-point and HDL blocks: FIR, mixer/NCO, decimator, measurement metrics and reproducible plots.

Блок 3 подготавливает DSP-примитивы, которые дальше переходят в fixed-point и HDL: FIR, mixer/NCO, decimator, метрики измерений и воспроизводимые графики.
