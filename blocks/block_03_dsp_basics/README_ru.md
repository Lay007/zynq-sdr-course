# Блок 3. Базовые DSP-операции

## Назначение

Блок 3 переводит студента от правильной интерпретации спектра к активной обработке IQ-данных: окна, FFT, фильтрация, цифровой перенос частоты, multirate-операции и базовые метрики.

![Block 3 Pipeline](assets/block03_pipeline.svg)

## Почему блок важен

Block 2 учит правильно читать сигнал. Block 3 учит сигнал изменять, очищать, переносить по частоте и подготавливать к FPGA-реализации.

Главная идея блока:

```text
IQ input -> FFT window -> FIR filter -> digital mix -> multirate -> metrics -> FPGA-ready DSP
```

## Основные темы

| Тема | Инженерный смысл |
|---|---|
| FFT windows | leakage, resolution, корректность измерений |
| FIR/IIR filtering | АЧХ, ФЧХ, переходная полоса, задержка |
| Digital mixing | перенос частоты через NCO/DDS и complex multiplication |
| Multirate DSP | decimation, interpolation, anti-aliasing, anti-imaging |
| Metrics | SNR, noise floor, spur level, engineering conclusion |
| FPGA preparation | fixed-point, latency, streaming interface, resource thinking |

## Практические лабораторные

| Lab | Тема | Основной артефакт | Связь с FPGA/RF |
|---|---|---|---|
| Lab 3.1 | FFT windows and leakage | сравнение спектров | дисциплина измерений |
| Lab 3.2 | FIR low-pass filtering of IQ data | АЧХ + отфильтрованный IQ | будущий FIR RTL-блок |
| Lab 3.3 | Digital mixing and frequency shift | спектр до/после переноса | NCO + complex multiplier |
| Lab 3.4 | Decimation with anti-aliasing filter | проверка anti-aliasing | rate-change блок для FPGA |

## Минимальный отчёт по каждой лабораторной

Каждая лабораторная должна давать не только картинку, но и инженерный вывод:

1. цель обработки;
2. параметры сигнала и `Fs`;
3. график до обработки;
4. график после обработки;
5. численная метрика или наблюдение;
6. что это означает для FPGA/RF-реализации.

## Инженерный результат

После блока студент должен уметь:

- выбирать окно FFT под задачу измерения;
- проектировать простой FIR-фильтр;
- объяснять задержку и переходную полосу;
- переносить сигнал по частоте в complex baseband;
- выполнять decimation/interpolation без разрушения спектра;
- связывать DSP-блок с будущей fixed-point/HDL реализацией;
- оформлять результаты в виде воспроизводимого отчёта.

## Связь с последующими блоками

Блок 3 подготавливает DSP-примитивы, которые дальше переходят в fixed-point и HDL:

- FIR -> streaming FIR RTL;
- digital mixer -> NCO + complex multiplier;
- decimation -> anti-aliasing + rate-change path;
- metrics -> automated validation and reports.
