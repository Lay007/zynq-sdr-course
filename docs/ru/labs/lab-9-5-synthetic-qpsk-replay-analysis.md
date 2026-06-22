# Lab 9.5 — Synthetic QPSK replay and constellation analysis

## Цель

В этой лабораторной работе студент проходит полный воспроизводимый цикл работы с IQ-данными без риска публикации реального эфира:

1. сгенерировать synthetic QPSK dataset;
2. прочитать CI16 IQ samples;
3. построить constellation и spectrum preview;
4. получить JSON-метрики;
5. связать результат с инженерным отчётом.

Эта лабораторная дополняет реальные RTL-SDR/Zynq наблюдения: реальные записи показывают практический RF-тракт, а synthetic QPSK даёт legally clean и полностью детерминированный тестовый сигнал для CI и обучения.

## Входные артефакты

| Артефакт | Назначение |
|---|---|
| `datasets/demo_qpsk_capture/manifest.yaml` | описание dataset и параметров сигнала |
| `datasets/demo_qpsk_capture/metrics.json` | базовые метрики генератора |
| `tools/generate_demo_qpsk_dataset.py` | deterministic генератор CI16 QPSK |
| `tools/analyze_demo_qpsk_dataset.py` | анализатор dataset и генератор preview assets |
| `reports/demo_qpsk_dataset_analysis.md` | отчётный пример для ревьюера |

## Команды воспроизведения

Из корня репозитория:

```bash
python tools/generate_demo_qpsk_dataset.py
python tools/analyze_demo_qpsk_dataset.py
```

Если CI16-файл отсутствует, можно запустить анализатор с автоматической генерацией:

```bash
python tools/analyze_demo_qpsk_dataset.py --generate-if-missing
```

## Ожидаемые выходные файлы

| Файл | Что проверять |
|---|---|
| `datasets/demo_qpsk_capture/demo_qpsk_capture.ci16` | локально сгенерированный IQ payload, не коммитится |
| `datasets/demo_qpsk_capture/analysis_summary.json` | sample count, EVM, CFO, bandwidth metrics |
| `docs/assets/demo_qpsk_constellation.svg` | четыре компактных QPSK-кластера |
| `docs/assets/demo_qpsk_spectrum.svg` | спектр synthetic QPSK сигнала |

## Контрольные метрики

Минимальные acceptance criteria:

| Метрика | Ожидаемое значение |
|---|---:|
| `num_samples` | `16384` |
| `num_symbols` | `2048` |
| `sample_rate_hz` | `2400000` |
| `evm_rms_percent` | `< 0.01` |
| `abs(cfo_estimate_hz)` | `< 1.0` |

## Инженерная интерпретация

Если метрики проходят пороги, значит:

- формат CI16 читается корректно;
- I/Q порядок не перепутан;
- выборка символов согласована с `samples_per_symbol`;
- constellation имеет ожидаемую структуру QPSK;
- analyzer может быть использован как базовый smoke test для будущих real-capture анализаторов.

## Impairment-мост к следующим лабораторным

Идеальный synthetic QPSK удобен как эталон. Следующий учебный шаг — намеренно внести искажения и посмотреть, как они проявляются в тех же метриках и графиках.

| Impairment | Что происходит с сигналом | Что смотреть в анализе | Связанный блок |
|---|---|---|---|
| CFO | constellation начинает вращаться от символа к символу | рост `cfo_estimate_hz`, смазывание кластеров | Block 8.1 CFO estimation/correction |
| Phase offset | все QPSK-точки поворачиваются на постоянный угол | constellation повернута, но кластеры остаются компактными | Block 8.2 Phase offset correction |
| Timing offset | выборка попадает не в центр символа | рост EVM, ухудшение кластеров, eye/символьная ошибка | Block 8.3 Timing recovery |
| AWGN | точки расплываются вокруг идеальных положений | рост `evm_rms_percent`, падение SNR estimate | Block 7.3 / Block 8 sync metrics |
| DC offset | constellation сдвигается от центра | ненулевые `mean_i_normalized` и `mean_q_normalized` | Block 6.5 RF impairment calibration |
| IQ imbalance | constellation растягивается/наклоняется, появляется image | асимметрия кластеров и image-компонента в спектре | Block 6.5 / Zero-IF artifacts |

Минимальная последовательность эксперимента:

1. сохранить baseline `analysis_summary.json` для идеального QPSK;
2. внести один impairment за раз;
3. повторить анализатор;
4. сравнить EVM, CFO, mean I/Q, spectrum и constellation;
5. записать, какая метрика первой показала проблему.

Такой подход связывает Block 9 с последующими темами синхронизации и RF-калибровки: один и тот же dataset становится сначала эталоном, затем controlled test signal для проверки алгоритмов компенсации.

## Что включить в отчёт

В отчёт по лабораторной добавить:

1. команды запуска;
2. фрагмент `analysis_summary.json`;
3. constellation preview;
4. spectrum preview;
5. короткий вывод: почему synthetic dataset полезен рядом с real RF captures;
6. таблицу baseline vs один выбранный impairment, если выполняется расширенное задание.

## CI-связь

Лабораторная покрыта workflow:

```text
.github/workflows/qpsk_demo_analysis.yml
```

CI проверяет, что dataset генерируется, анализатор выполняется, выходные файлы создаются, а ключевые метрики проходят пороги.

## Следующий шаг

После этой лабораторной можно добавить отдельный скрипт controlled impairments: CFO, DC offset, IQ imbalance, AWGN и timing offset. Это превратит идеальный QPSK fixture в тестовый стенд для проверки синхронизации и RF-калибровки.
