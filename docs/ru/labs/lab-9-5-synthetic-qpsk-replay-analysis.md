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

## Что включить в отчёт

В отчёт по лабораторной добавить:

1. команды запуска;
2. фрагмент `analysis_summary.json`;
3. constellation preview;
4. spectrum preview;
5. короткий вывод: почему synthetic dataset полезен рядом с real RF captures.

## CI-связь

Лабораторная покрыта workflow:

```text
.github/workflows/qpsk_demo_analysis.yml
```

CI проверяет, что dataset генерируется, анализатор выполняется, выходные файлы создаются, а ключевые метрики проходят пороги.

## Следующий шаг

После этой лабораторной можно переходить к сравнению synthetic QPSK с реальными IQ-записями и к добавлению impairment-моделей: CFO, DC offset, IQ imbalance, AWGN и timing offset.
