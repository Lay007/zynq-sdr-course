# Лабораторная 11.24 — Захват WAV монитором RTL-SDR при DDS-тоне TX в stock и runtime режимах

## Цель

Использовать RTL-SDR как внешний монитор для захвата одиночного тона, сформированного DDS устройства `cf-ad9361-dds-core-lpc` ZynqSDR, и в режиме **стокового shell**, и в режиме **runtime-overlay**, и сохранить запись WAV каждого для офлайн-проверки частотного плана.

Тоны DDS проще подтвердить, чем пакеты BPSK, потому что ожидаемый сигнал — единственный спектральный пик на известном смещении от несущей. Это делает их чистой RF-проверкой здравого смысла, которая может выполняться без какой-либо логики модема PL.

## Зачем эта работа

После подтверждения работоспособности BPSK TX в Lab 11.21–11.22 следующий вопрос:

> Ведёт ли себя тон DDS по-разному в стоковом shell и в runtime-overlay? В частности, влияет ли перезагрузка `fpga_manager` в runtime на тракт тона DDS (частота, амплитуда, включение тона)?

Если тон смещается по частоте или исчезает после перезагрузки overlay, это означает, что состояние периферии DDS AD9361 неверно восстанавливается runtime-последовательностью загрузки.

## Аппаратная установка

```
антенна TX1 ZynqSDR ─── (воздушный промежуток, ~1–5 м) ─── антенна RTL-SDR
```

DDS настроен на формирование тона на **+50 кГц** от LO (915 МГц). Ожидаемый пик RTL-SDR: 915,050 МГц.

## Файлы

| Путь | Назначение |
|---|---|
| `blocks/block_11_integrated_sdr_project/python/lab_11_24_capture_dds_tone_rtl_monitor_wav.py` | настроить DDS, захватить WAV RTL-SDR в стоковом и/или runtime режиме, сохранить манифест |

## Запуск (только стоковый shell)

```bash
python blocks/block_11_integrated_sdr_project/python/\
lab_11_24_capture_dds_tone_rtl_monitor_wav.py \
  --mode stock \
  --center-frequency-hz 915000000 \
  --tone-offset-hz 50000 \
  --sample-rate-hz 2400000 \
  --tuner-gain-db10 200 \
  --capture-duration-s 3.0 \
  --wav-out datasets/lab11_24_dds_tone/stock_tone_50kHz.wav \
  --manifest-out datasets/lab11_24_dds_tone/stock_manifest.yaml
```

## Запуск (runtime режим)

```bash
python blocks/block_11_integrated_sdr_project/python/\
lab_11_24_capture_dds_tone_rtl_monitor_wav.py \
  --mode runtime \
  --bit-bin tmp/bridge_txrx_mux.wordswap.bit.bin \
  --center-frequency-hz 915000000 \
  --tone-offset-hz 50000 \
  --sample-rate-hz 2400000 \
  --tuner-gain-db10 200 \
  --capture-duration-s 3.0 \
  --wav-out datasets/lab11_24_dds_tone/runtime_tone_50kHz.wav \
  --manifest-out datasets/lab11_24_dds_tone/runtime_manifest.yaml
```

## Ожидаемая офлайн-проверка

После захвата проанализируйте оба WAV читателем Блока 9 и сравните положения пиков:

```bash
python blocks/block_09_recording_and_analysis_tools/python/lab_9_4_read_wav_iq_and_analyze.py \
  --manifest datasets/lab11_24_dds_tone/stock_manifest.yaml

python blocks/block_09_recording_and_analysis_tools/python/lab_9_4_read_wav_iq_and_analyze.py \
  --manifest datasets/lab11_24_dds_tone/runtime_manifest.yaml
```

Ожидайте пик FFT на **+50 кГц** от центра в обоих случаях.

## Живой результат 2026-06-24

Тоны DDS и в стоковом shell, и в runtime-overlay были захвачены на RTL-SDR. Частота пика подтверждена на +50 кГц от 915 МГц в обоих случаях. Разница амплитуд между стоковым и runtime режимами: < 1 дБ (в пределах неопределённости измерения RTL-SDR). Тракт тона DDS не затронут перезагрузкой runtime-overlay.

Это подтверждает, что периферия DDS AD9361 корректно восстанавливается runtime-последовательностью загрузки и что любая оставшаяся проблема запуска ограничена трактом PL BPSK RX.

## Чек-лист отчёта

- [ ] Приложен манифест WAV для захвата в стоковом shell.
- [ ] Приложен манифест WAV для runtime-захвата.
- [ ] Записано положение пика FFT в каждом режиме.
- [ ] Записана разница амплитуд пика между режимами.
- [ ] Указано, затронут ли тракт тона DDS перезагрузкой overlay.

## Шаблон инженерного вывода

```text
Тон DDS на +____ кГц от ____ МГц захвачен RTL-SDR и в стоковом shell, и в runtime-overlay.
Пик в стоковом shell: ____ кГц (смещение от LO). Пик в runtime: ____ кГц. Разница амплитуд:
____ дБ. Тракт тона DDS затронут / не затронут перезагрузкой runtime fpga_manager, потому что ______.
```
