# Lab 11.38 — ZynqSDR TX → запись IQ → офлайн-приёмник

## Идея

Перед тем как переносить весь RX в PL второй платы, полезно разделить задачу на две части:

```text
ZynqSDR A
PS / packet source
      ↓
PL: существующий QPSK TX
      ↓
AD936x TX
      ↓ RF / cable
      ↓
┌───────────────────────────────┐
│ вариант A: ZynqSDR B + AD936x │
│ вариант B: RTL-SDR            │
└───────────────────────────────┘
      ↓
raw IQ capture + metadata
      ↓
MATLAB / Python reference RX
      ↓
CFO → matched filter → timing → carrier recovery
      ↓
frame sync → QPSK demap → packet decode → CRC
      ↓
"Hello from board A"
```

Передатчик уже настоящий аппаратный. Приём пока остаётся максимально наблюдаемым: каждый DSP-этап можно построить на графике, сравнить с эталоном и повторить на одном и том же IQ-файле.

## Почему этот этап нужен до real-time RX в PL

Если сразу собирать двухплатный тракт с аппаратным TX и аппаратным RX, при ошибке трудно локализовать источник:

- передатчик;
- RF path;
- частотная ошибка;
- sample-rate mismatch;
- matched filter;
- timing recovery;
- carrier recovery;
- frame synchronization;
- packet framing.

Сохранённый IQ-файл разделяет проблему:

```text
hardware TX + RF + ADC   |   deterministic offline RX
```

После записи один и тот же capture можно многократно прогонять через MATLAB/Python, fixed-point модель и затем через RTL-replay. Так появляется честный golden reference для будущего PL RX.

## Два варианта приёмника

### Вариант A — вторая ZynqSDR

```text
AD936x RX → IIO capture → .ci16 + .json
```

Преимущества:

- архитектура RX ближе к будущей второй плате;
- больше разрядность IQ;
- удобно сравнивать с последующим real-time Zynq RX;
- можно записывать с sample rate, удобным для модели.

### Вариант B — RTL-SDR

```text
RTL-SDR → rtl_sdr / compatible recorder → .cu8 + .json
```

Преимущества:

- дешёвый независимый наблюдатель;
- хороший инструмент для доказательства, что сигнал реально существует в эфире;
- намеренно добавляет реальные ограничения: 8-bit IQ, DC spur, oscillator ppm/CFO и другой sample rate.

RTL-SDR не должен искусственно подгоняться под sample rate передатчика. В метаданных фиксируется **реальный capture sample rate**, а офлайн-модель при необходимости выполняет рациональный resampling к своей рабочей частоте.

## Обязательный контракт записи

Использовать существующий [IQ recording metadata guide](../../iq-recording-metadata.md).

Каждый capture состоит минимум из двух файлов:

```text
qpsk_hw_tx_capture_001.ci16   # ZynqSDR RX
qpsk_hw_tx_capture_001.json
```

или

```text
qpsk_hw_tx_capture_001.cu8    # RTL-SDR RX
qpsk_hw_tx_capture_001.json
```

В JSON обязательно сохранить:

- TX board/build identity;
- RX device;
- center frequency;
- RX sample rate;
- RX gain mode и gain;
- RF bandwidth;
- attenuation / cable path;
- IQ format;
- число samples;
- переданный packet sequence;
- ожидаемый payload или PRBS seed.

IQ-файл без metadata не считается воспроизводимым результатом лабораторной.

## Этап 1 — аппаратный передатчик

Использовать уже существующий QPSK TX datapath курса. Новый PHY для этой лаборатории не создаётся.

Для первого PASS удобнее передавать повторяющийся фиксированный кадр с известным payload. После интеграции packet bridge можно использовать тот же 32-byte packet v1, что и в Lab 11.46.

Перед началом записи проверить:

- TX center frequency;
- sample rate;
- TX gain;
- отсутствие перегрузки проводного RX;
- достаточное затухание при cable test.

## Этап 2 — запись IQ

Записать достаточно длинный участок, содержащий несколько кадров и свободный интервал до/после них.

Не обрезать capture вручную до «красивого» пакета. Офлайн-приёмник должен сам найти кадр внутри более длинной записи.

Для RTL-SDR отдельно сохранить фактический `sample_rate_hz`; он может отличаться от sample rate TX и от внутренней частоты модели.

## Этап 3 — нормализация входа

Офлайн-модель должна начинаться с адаптера формата:

```text
.cu8 / .ci16
      ↓
complex floating-point reference samples
      ↓
DC removal / normalization
      ↓
optional rational resampler
```

Нельзя скрывать этот этап внутри последующего DSP. Студент должен видеть, что `cu8`, `ci16` и модельные complex samples — это разные представления одного сигнала.

### Исполняемый Python baseline

Первый детерминированный приёмник реализован в:

```text
blocks/block_11_integrated_sdr_project/python/lab_11_38_offline_qpsk_rx.py
```

Сначала обязательно запустить self-test без аппаратуры:

```bash
python blocks/block_11_integrated_sdr_project/python/lab_11_38_offline_qpsk_rx.py --self-test
```

Self-test помещает один известный кадр курса внутрь более длинной записи и добавляет неизвестный sample offset, начальную фазу, CFO, DC offset и AWGN. Его PASS означает, что **офлайн-алгоритм** умеет самостоятельно захватить и декодировать эталонную запись. Это не является доказательством приёма реального сигнала ZynqSDR или RTL-SDR.

Для реальной записи ZynqSDR в `ci16`:

```bash
python blocks/block_11_integrated_sdr_project/python/lab_11_38_offline_qpsk_rx.py \
  measurements/qpsk_hw_tx_capture_001.ci16 \
  --output measurements/qpsk_hw_tx_capture_001_rx.json
```

Metadata sidecar автоматически берётся из файла:

```text
measurements/qpsk_hw_tx_capture_001.json
```

Та же команда работает для записи RTL-SDR `.cu8`, если в sidecar указано `"iq_format": "cu8"`. Приёмник использует **реальный** `sampling.sample_rate_hz` из JSON. Например, запись RTL-SDR 2.4 MS/s явно преобразуется в рабочие 3.84 MS/s модели курса рациональным отношением `8/5`; код не делает вид, что тактовые частоты двух трактов одинаковы.

Текущий Python baseline выполняет следующую исполняемую цепочку:

```text
raw ci16/cu8/cf32 + JSON metadata
  ↓
явное преобразование числового формата
  ↓
DC removal + RMS normalization
  ↓
rational sample-rate conversion при необходимости
  ↓
совпадающий с курсом 65-tap RRC matched filter
  ↓
перебор всех 8 целочисленных sample phases
  ↓
4th-power coarse CFO acquisition для QPSK
  ↓
normalized preamble correlation / автоматический frame start
  ↓
оценка residual carrier phase/CFO по преамбуле
  ↓
QPSK hard decisions
  ↓
BER + EVM + CFO + sync metric в JSON
```

Для baseline QPSK 480 kSym/s однозначный диапазон захвата fourth-power CFO estimator составляет примерно ±60 кГц. Если реальный RTL-SDR даёт большую частотную ошибку, нужно точнее настроить RF или позже добавить отдельный wide-range coarse-CFO stage. Нельзя маскировать это ручным поворотом уже готового constellation.

Текущая версия v1 декодирует сохранённый в репозитории **известный кадр 140 symbols / 280 bits**. Разбор packet-v1, sequence и CRC относится к будущему packet bridge Lab 11.46 и пока намеренно не заявляется как реализованный.

## Этап 4 — последовательный reference RX и диагностика

Рекомендуемый порядок:

```text
1. spectrum / waterfall sanity check
2. coarse CFO estimate
3. CFO correction
4. RRC matched filter
5. timing recovery
6. residual carrier / phase recovery
7. frame synchronization
8. QPSK decisions
9. payload recovery
10. CRC / BER / EVM metrics
```

На каждом этапе сохранять хотя бы один диагностический результат, а не только финальный BER.

Отдельный диагностический инструмент использует те же функции приёмника:

```text
blocks/block_11_integrated_sdr_project/python/offline_qpsk_diagnostics.py
```

Сначала проверить его на synthetic/reference записи:

```bash
python blocks/block_11_integrated_sdr_project/python/offline_qpsk_diagnostics.py \
  --self-test \
  --plot-dir measurements/lab1138_selftest_plots
```

Для реального capture:

```bash
python blocks/block_11_integrated_sdr_project/python/offline_qpsk_diagnostics.py \
  measurements/qpsk_hw_tx_capture_001.ci16 \
  --plot-dir measurements/qpsk_hw_tx_capture_001_plots
```

Инструмент сохраняет пять независимых PNG:

```text
spectrum.png
sync-metric.png
constellation-before-carrier-correction.png
constellation-after-carrier-correction.png
matched-filter-timing.png
```

Plotter намеренно вызывает тот же format adapter, rational resampler, RRC, CFO estimator и frame-acquisition code, что и числовой receiver. Поэтому графики показывают работу настоящей reference-цепочки, а не отдельного упрощённого анализатора. CI проверяет создание всех пяти PNG из необрезанной synthetic/reference записи.

## Этап 5 — декодирование сообщения

После появления packet bridge использовать тот же application packet, что и в Lab 11.46:

```text
byte 0      : payload length
bytes 1..2  : sequence
bytes 3..29 : application bytes
bytes 30..31: CRC-16/CCITT
```

Тогда acceptance result становится понятным без анализа битовых массивов:

```text
capture: qpsk_hw_tx_capture_017.cu8
sequence: 17
crc: OK
payload: "Hello from board A"
```

До появления packet bridge допускается известный PRBS/payload с BER-сравнением.

## Этап 6 — сравнение двух RX устройств

Если доступны и ZynqSDR B, и RTL-SDR, записать один и тот же TX двумя приёмниками при максимально близких условиях.

Сравнить:

| Metric | ZynqSDR RX | RTL-SDR RX |
|---|---:|---:|
| sample rate | measured | measured |
| estimated CFO | | |
| EVM after sync | | |
| decoded frames | | |
| CRC OK | | |
| BER/PER | | |

Это связывает лабораторию с уже существующим receiver-comparison материалом Block 6.

## Ключевой учебный переход

После успешного офлайн-декодирования следующий RX строится не «с нуля». Блоки переносятся по одному:

```text
captured IQ
  ↓
MATLAB/Python float RX        ← golden reference
  ↓
fixed-point RX
  ↓
RTL block replay on same IQ
  ↓
PL streaming RX
  ↓
real-time two-board RX
```

Для каждого перенесённого блока желательно сохранять один и тот же входной capture и сравнивать выходы sample-by-sample или metric-by-metric.

## Что считается PASS

Минимальный hardware/offline PASS:

1. сигнал физически сформирован ZynqSDR TX;
2. IQ записан независимым RX устройством;
3. capture имеет корректный metadata sidecar;
4. reference model самостоятельно находит и синхронизирует кадр;
5. payload/PRBS восстановлен;
6. сохранены CFO и минимум одна quality metric (`EVM`, `BER` или `CRC`);
7. результат можно повторить, не выполняя новую RF-запись.

Это **hardware TX + real RF/IQ capture + offline model evidence**. Это ещё не доказательство real-time PL RX.

CI/self-test `lab_11_38_offline_qpsk_rx.py` и diagnostic plotter закрывают только программную/reference часть пунктов 3–6. Лаборатория остаётся hardware-pending, пока этой цепочкой не обработана настоящая RF/IQ запись.

## Следующий шаг

После PASS этой лаборатории переходить к Lab 11.45 (дифференциальный QPSK и длинная преамбула), а затем к [Lab 11.46 — сообщение из консоли одной Zynq в консоль другой](lab-11-46-two-board-console-message.md), постепенно заменяя offline reference RX аппаратными блоками второй платы.
