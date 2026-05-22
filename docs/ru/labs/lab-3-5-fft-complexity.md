# Lab 3.5 — сложность FFT и selected-bin detection

Эта лабораторная усиливает фундамент DSP без notebook-подхода. Это детерминированная script-driven работа, которая связывает вычислительную сложность спектрального анализа с SDR-измерениями и FPGA-архитектурой.

## Цель

Сравнить три стратегии анализа:

| Стратегия | Когда полезна | Инженерное следствие |
|---|---|---|
| Direct DFT | Малые эталонные векторы и обучение. | Простая, но плохо масштабируется. |
| Full FFT | Spectrum display, measurement dashboard и неизвестные сигналы. | Эффективный полный спектр, но появляются требования к памяти, порядку данных и архитектуре. |
| Selected-bin detection | Известные тоны, пилоты, узкополосные проверки. | Может быть дешевле FFT, если нужны только несколько частот. |

## Команда запуска

Из корня репозитория:

```bash
python blocks/block_03_dsp_basics/python/lab_3_5_fft_complexity.py
```

Или через общий reproducibility suite:

```bash
python tools/run_all_labs.py
```

## Генерируемые артефакты

| Артефакт | Назначение |
|---|---|
| `docs/assets/lab35_dft_fft_complexity.png` | Рост вычислительных затрат Direct DFT и FFT. |
| `docs/assets/lab35_selected_bin_tradeoff.png` | Full-spectrum FFT против selected-bin detector. |
| `docs/assets/lab35_fft_complexity_metrics.json` | Машиночитаемые отношения сложности для CI и отчёта. |

## Инженерные вопросы

1. Начиная с каких размеров `N` direct DFT становится непрактичной для SDR-анализа?
2. Когда оправдан полный FFT, а когда selected-bin detection?
3. Как изменится выбор при FPGA streaming design?
4. Какие компромиссы по памяти и latency возникают при переходе от скрипта к RTL?

## Что включить в отчёт

- Оба сгенерированных графика.
- Отношение сложности DFT/FFT на максимальном `N`.
- Отношение FFT/selected-bin на максимальном `N`.
- Обоснование выбора метода для:
  - мониторинга спектра;
  - обнаружения одиночного pilot tone;
  - wideband unknown-signal search;
  - FPGA-реализации с ограниченными ресурсами.

## Связь со следующими блоками

Эта лабораторная напрямую связана с:

- Block 05: ресурсы FFT и streaming architecture;
- Block 08: обнаружение pilot/synchronization;
- Block 09: анализ спектра записанных IQ;
- Block 11: measurement dashboard design.
