# Lab 1.1 — Управляемый DDS-тон Zynq с приемом на RTL-SDR

## Назначение

Эта лабораторная работа замыкает первый управляемый RF-цикл курса:

```text
Zynq + AD9361 DDS tone -> короткий RF-путь -> захват RTL-SDR -> WAV IQ -> офлайн-анализ спектра
```

В отличие от Lab 1.0, источник сигнала теперь известен заранее. Студент не просто наблюдает эфир, а проверяет, подтверждает ли внешний приемник именно тот сигнал, который должен формировать передатчик.

## Зачем это нужно

Одиночный тон удобен как первый управляемый witness для:

- настройки несущей;
- проверки согласованности sample rate;
- дисциплины по уровням TX/RX;
- поиска клиппинга и перегрузки;
- воспроизводимой IQ-записи с метаданными.

Если этот шаг работает, то дальнейшие лабораторные по BPSK/QPSK уже опираются на проверенный RF-baseline.

## Живой опорный прогон

В репозитории теперь есть реальный `stock-shell` прогон, снятый `2026-06-24`, со следующими параметрами:

| Параметр | Значение |
|---|---:|
| Несущая | `915 MHz` |
| Tone offset | `200 kHz` |
| Sample rate на Zynq | `3.84 MS/s` |
| Sample rate RTL-SDR | `2.4 MS/s` |
| TX attenuation | `-40 dB` |
| Tuner gain RTL-SDR | `20.0 dB` |
| Масштаб тона | `0.25` |

Измеренный результат офлайн-анализатора WAV:

| Метрика | Значение |
|---|---:|
| Измеренный пик | `202624.512 Hz` |
| Ошибка частоты | `+2624.512 Hz` |
| Оценка SNR | `66.40 dB` |
| Доля клиппинга | `0` |
| Quality gate | `PASS` |

## Артефакты

- Capture report: `docs/assets/lab1124_dds_tone_rtl_monitor_live_20260624_stock_dds_tone_ref_a.json`
- Metrics JSON: `docs/assets/lab11_24_dds_tone_rtl_monitor_live_20260624_stock_dds_tone_ref_a_metrics.json`
- Dataset manifest: `datasets/lab11_24_dds_tone_rtl_monitor/manifest_live_20260624_stock_dds_tone_ref_a.yaml`
- График спектра:

![Управляемый спектр stock-shell DDS tone](../../assets/lab94_lab11_24_dds_tone_rtl_monitor_live_20260624_stock_dds_tone_ref_a_spectrum.png)

- Краткий time preview:

![Time preview для stock-shell DDS tone](../../assets/lab94_lab11_24_dds_tone_rtl_monitor_live_20260624_stock_dds_tone_ref_a_time_preview.png)

## Воспроизведение

Захват:

```powershell
python blocks/block_11_integrated_sdr_project/python/lab_11_24_capture_dds_tone_rtl_monitor_wav.py `
  --mode stock `
  --run-tag live_20260624_stock_dds_tone_ref_a `
  --tone-offset-hz 200000 `
  --tone-scale 0.25 `
  --tx-attenuation-db -40 `
  --rx-gain-db 10 `
  --rtl-tuner-gain-db10 200 `
  --no-reboot-after
```

Офлайн-анализ:

```powershell
python blocks/block_09_recording_and_analysis_tools/python/lab_9_4_read_wav_iq_and_analyze.py `
  --manifest datasets/lab11_24_dds_tone_rtl_monitor/manifest_live_20260624_stock_dds_tone_ref_a.yaml
```

## Инженерная интерпретация

Этот прогон закрывает первый управляемый пример с внешним приемником для Block 1:

- тон виден на ожидаемом смещении;
- частотная ошибка невелика и объяснима рассогласованием LO/tuner;
- SNR достаточно высокий для хорошего учебного отчета;
- тот же WAV manifest потом можно напрямую переиспользовать в Block 9.

## Runtime-расширение

Тот же helper сначала был запущен на настоящем `runtime bridge_txrx_mux` overlay:

- report: `docs/assets/lab1124_dds_tone_rtl_monitor_live_20260624_runtime_dds_tone_ref_a.json`
- metrics: `docs/assets/lab11_24_dds_tone_rtl_monitor_live_20260624_runtime_dds_tone_ref_a_metrics.json`

Этот runtime-прогон tone quality gate не прошел: ожидаемый тон на `200 kHz` исчез, а главный внешний пик схлопнулся почти в DC.

После этого witness был повторен и на более минимальных runtime-payload'ах:

| Payload | Измеренный пик | Оценка SNR | Quality gate | Интерпретация |
|---|---:|---:|---|---|
| `stock-shell` | `202624.5 Hz` | `66.4 dB` | `PASS` | Ожидаемый внешний тон `200 kHz` хорошо виден |
| `vendor_only` | `2600.1 Hz` | `35.9 dB` | `FAIL` | Доминирующий пик схлопывается к DC |
| `gpreg_only` | `2636.7 Hz` | `36.9 dB` | `FAIL` | Тот же near-DC collapse |
| `bridge_rx_only` | `2636.7 Hz` | `36.9 dB` | `FAIL` | Тот же near-DC collapse |
| `bridge_txrx_mux` | `2636.7 Hz` | `38.7 dB` | `FAIL` | Тот же near-DC collapse |

Расширенные артефакты:

- `docs/assets/lab1124_dds_tone_rtl_monitor_live_20260624_vendor_only_dds_tone_a.json`
- `docs/assets/lab1124_dds_tone_rtl_monitor_live_20260624_gpreg_only_dds_tone_a.json`
- `docs/assets/lab1124_dds_tone_rtl_monitor_live_20260624_bridge_rx_only_dds_tone_a.json`
- `docs/assets/lab1125_stock_vs_runtime_dds_tone_sweep_live_20260624_sync_arm_test_a.json`

Это уже было сильнее исходного наблюдения только для `bridge_txrx_mux`. Даже минимальные editable non-stock shell-варианты теряли внешний DDS witness, а значит текущий Block 11 blocker сидел в самом runtime shell / hot-load RF path, а не в более поздней course BPSK bridge-логике.

После этого был проведен repair-эксперимент с явной post-reload переинициализацией DDS-core:

| Payload + repair | Измеренный пик | Оценка SNR | Quality gate | Интерпретация |
|---|---:|---:|---|---|
| `vendor_only + cf_axi_dds rebind + RATECNTRL=3` | `202624.5 Hz` | `66.5 dB` | `PASS` | Внешний тон `200 kHz` полностью восстановлен |
| `bridge_txrx_mux + cf_axi_dds rebind + RATECNTRL=3` | `202624.5 Hz` | `66.0 dB` | `PASS` | Полный course overlay снова дает внешний TX witness |

Артефакты repair-ветки:

- `docs/assets/lab1124_dds_tone_rtl_monitor_live_20260624_vendor_only_dds_tone_rebind_dds_a.json`
- `docs/assets/lab1124_dds_tone_rtl_monitor_live_20260624_vendor_only_dds_tone_rebind_dds_rate3_a.json`
- `docs/assets/lab1124_dds_tone_rtl_monitor_live_20260624_bridge_txrx_mux_dds_tone_rebind_dds_rate3_a.json`

Промежуточный прогон только с `cf_axi_dds` rebind уже возвращал сигнал, но примерно на `800 kHz` вместо `200 kHz`. Это локализовало еще один недостающий post-reload шаг: нужно было вернуть DAC rate-control register в штатное значение `3`.

Из-за этого лабораторная теперь полезна далеко не только для Block 1. Она одновременно служит:

- первым управляемым external-receiver experiment курса;
- чистым Block 11 witness, который доказывает, что внешний TX-path failure после runtime reload в принципе исправим через post-reload AXI DDS re-initialization.
