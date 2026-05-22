# Lab 7.5 — CIC-дециматор для SDR-приёмника

Эта лабораторная усиливает мост DSP → fixed-point → FPGA. Это не notebook-упражнение, а детерминированная script-driven лабораторная работа, которая генерирует графики и machine-readable метрики для CI.

## Цель

Смоделировать CIC-дециматор как аппаратно-ориентированный multirate-блок и измерить:

- АЧХ CIC-фильтра;
- поведение при децимации;
- aliasing мешающего тона после изменения частоты дискретизации;
- passband droop;
- рост разрядности аккумуляторов;
- fixed-point последствия для RTL-реализации.

## Почему CIC важен

CIC-дециматор полезен в SDR-приёмниках, потому что может снижать высокую входную частоту дискретизации при помощи сумматоров, вычитателей и задержек без умножителей. Это делает его естественным мостом от теории DSP к FPGA-реализации.

Типичное место в тракте приёмника:

```text
RF frontend / ADC stream -> CIC decimator -> compensation FIR -> channel filter -> demodulator
```

## Команда запуска

Из корня репозитория:

```bash
python blocks/block_07_tx_rx_chains/python/lab_7_5_cic_decimator.py
```

Или через общий executable smoke path:

```bash
python tools/run_all_labs.py
```

## Генерируемые артефакты

| Артефакт | Назначение |
|---|---|
| `docs/assets/lab75_cic_response.png` | АЧХ CIC и droop на частоте полезного тона. |
| `docs/assets/lab75_cic_decimation_spectrum.png` | Спектр входа и спектр после CIC-децимации. |
| `docs/assets/lab75_cic_bit_growth.png` | Требуемая ширина аккумуляторов в зависимости от числа каскадов. |
| `docs/assets/lab75_cic_metrics.json` | Частоты дискретизации, коэффициент децимации, рост разрядности и измеренная частота пика. |

## Инженерные вопросы

1. Почему CIC удобен для высокоскоростной децимации в FPGA?
2. Как оценить рост разрядности для `N` каскадов, коэффициента децимации `R` и differential delay `M`?
3. Что происходит с мешающим тоном после децимации?
4. Почему passband droop важен для SDR-цепочек, где оцениваются EVM/SNR/BER?
5. Где после CIC нужно поставить compensation FIR?

## Что включить в отчёт

- параметры CIC: `R`, `N`, `M`;
- входную и выходную частоты дискретизации;
- рекомендуемую ширину аккумуляторов;
- passband droop на частоте полезного сигнала;
- alias-частоту мешающего тона после децимации;
- сгенерированные графики;
- комментарии по fixed-point scaling и overflow behavior.

## Следующий RTL-шаг

Следующая FPGA-лабораторная должна отобразить ту же структуру в RTL:

```text
integrator stages -> decimation enable -> comb stages -> output valid
```

и сравнить RTL-выход с Python fixed-point-style моделью.

См. также: [CIC, fixed-point and FPGA bridge](../../cic-fixed-point-fpga-bridge.md).
