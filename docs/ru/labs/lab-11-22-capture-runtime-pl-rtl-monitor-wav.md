# Лабораторная 11.22 — Захват WAV монитором RTL-SDR во время runtime/PL-запуска BPSK

## Цель

Выполнить тот же подход внешнего мониторинга RTL-SDR, что и в Lab 11.21, но при работе ZynqSDR под **runtime-overlay курса** (`bridge_txrx_mux`) вместо стокового shell. Цель — подтвердить, действительно ли тракт PL BPSK TX излучает RF-сигнал даже при `rx_valid_count = 0`, что изолировало бы отказ только на стороне RX.

## Инженерный вопрос

> Если `tx_valid_count > 0` в overlay PL, но монитор RTL-SDR не видит сигнала, значит, тракт ЦАП PL TX сломан. Если RTL-SDR сигнал видит, чинить нужно только тракт PL RX.

## Аппаратная установка

Та же физическая схема, что в Lab 11.21:

```text
антенна TX1 ZynqSDR  ─── (воздушный промежуток, ~1–5 м) ───  антенна RTL-SDR
```

Проверяемый overlay — `bridge_txrx_mux.wordswap.bit.bin`.

## Файлы

| Путь | Назначение |
|---|---|
| `blocks/block_11_integrated_sdr_project/python/lab_11_22_capture_runtime_pl_rtl_monitor_wav.py` | загрузить runtime-overlay, запустить bring-up PL, одновременно захватить WAV RTL-SDR |

## Запуск

```bash
python blocks/block_11_integrated_sdr_project/python/\
lab_11_22_capture_runtime_pl_rtl_monitor_wav.py \
  --bit-bin tmp/bridge_txrx_mux.wordswap.bit.bin \
  --center-frequency-hz 915000000 \
  --sample-rate-hz 2400000 \
  --tuner-gain-db10 200 \
  --capture-duration-s 10.0 \
  --wav-out datasets/lab11_22_runtime_rtl_monitor/capture_live.wav \
  --manifest-out datasets/lab11_22_runtime_rtl_monitor/manifest_live.yaml \
  --run-tag runtime_pl_bpsk_rtl_monitor
```

Скрипт:

1. загружает runtime-overlay через `fpga_manager`;
2. проверяет ID `axi_gpreg` (0x4250534B);
3. настраивает TX/RX AD9361 на 915 МГц;
4. выставляет `burst_start`;
5. одновременно записывает WAV RTL-SDR в течение `--capture-duration-s` секунд;
6. считывает итоговые `tx_valid_count`, `rx_valid_count`, `received_bits`;
7. восстанавливает AD9361, сохраняет WAV и манифест, при необходимости перезагружает.

## Параллельный поток мониторинга

Захват RTL-SDR работает в фоновом потоке, пока основной поток управляет последовательностью запуска PL. Синхронизация потоков — через `threading.Event`: поток захвата пишет с момента выставления `burst_start` до установки события в конце `--capture-duration-s`.

## Живой результат 2026-06-23 — исправлено

> **Исправление.** В прежней версии этого раздела говорилось, что офлайн-анализ «обнаружил преамбулу
> BPSK и измерил BER = 0 / EVM ≈ 56 %», и делался вывод, что «тракт PL BPSK TX корректно излучает».
> Закоммиченный результат анализа этого не подтверждает. Запись runtime-PL прогона даёт
> **105 ошибочных бит из 281 (BER 0,37)**, EVM ≈ 820 % и корреляцию преамбулы 0,13 — признак полного
> отсутствия BPSK-сигнала ([метрики](/zynq-sdr-course/assets/lab1120_lab11_22_runtime_pl_rtl_monitor_live_20260624_runtime_pl_a_live_20260624_runtime_pl_a_metrics.json)).

Прогон действительно показал картину gpreg `tx_valid_count > 0`, `rx_valid_count = 0`. Счётчики
доказывают, что PL-модем выдавал отсчёты, но не доказывают, что отсчёты дошли до ЦАП. Лабораторная 11.26
установила, что не дошли: после перезагрузки оверлея DAC-ядро AD9361 поднимается в режиме DDS-only и
игнорирует поток из PL ([Лабораторная 11.26](/zynq-sdr-course/ru/labs/lab-11-26-runtime-dds-bypass-bpsk-ota/)).

Урок — тот, что эта страница сначала упустила: счётчик внутри FPGA не доказывает, что сигнал излучён.
Это может сказать только независимый приёмник, и здесь он сказал «нет».

## Чек-лист отчёта

- [ ] Подтверждён ID `axi_gpreg` до захвата.
- [ ] Записан `tx_valid_count` в конце захвата.
- [ ] Записан `rx_valid_count` в конце захвата.
- [ ] Приложен манифест WAV RTL-SDR.
- [ ] Проведена перекрёстная ссылка на офлайн-BER Lab 11.20 для этого WAV.

## Шаблон инженерного вывода

```text
Overlay runtime bridge_txrx_mux загружен, ID axi_gpreg = 0x____. Во время ____-секундного захвата
RTL-SDR на ____ МГц tx_valid_count = ____ и rx_valid_count = ____. Офлайн-результат BER Lab 11.20
для этого WAV: ____, EVM = ____ %. Вывод: PL TX излучает / не излучает. Нехватка данных RX
изолирована / не изолирована в тракте DMA AD9361→PL.
```
