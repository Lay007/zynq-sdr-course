# Курс SDR на Zynq

[![MkDocs](https://img.shields.io/badge/site-MkDocs%20Material-informational)](mkdocs.yml)
[![Full Course Smoke](https://github.com/Lay007/zynq-sdr-course/actions/workflows/full_course_smoke.yml/badge.svg)](https://github.com/Lay007/zynq-sdr-course/actions/workflows/full_course_smoke.yml)
[![Block 5 HDL](https://github.com/Lay007/zynq-sdr-course/actions/workflows/block5_hdl.yml/badge.svg)](https://github.com/Lay007/zynq-sdr-course/actions/workflows/block5_hdl.yml)
[![Block 8 Sync](https://github.com/Lay007/zynq-sdr-course/actions/workflows/block8_sync.yml/badge.svg)](https://github.com/Lay007/zynq-sdr-course/actions/workflows/block8_sync.yml)
[![Block 9 Recording](https://github.com/Lay007/zynq-sdr-course/actions/workflows/block9_recording_analysis.yml/badge.svg)](https://github.com/Lay007/zynq-sdr-course/actions/workflows/block9_recording_analysis.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Alexander%20Lyubko%20DSP-blue?logo=linkedin)](https://ru.linkedin.com/in/alexander-lyubko-dsp)

> Практический инженерный курс по Software-Defined Radio: DSP, fixed-point, FPGA/HDL, Zynq, радиотракт, измерения и воспроизводимая отчётность.

**English version:** [README.md](README.md)

![Zynq SDR Course Pipeline](docs/assets/course_pipeline.svg)

---

## Обзор

`zynq-sdr-course` — это инженерный курс по SDR, построенный вокруг полного маршрута от модели до измерения:

```text
теория -> DSP-модель -> fixed-point -> HDL/FPGA -> Zynq/AD9363 -> RF-тракт -> запись IQ -> анализ -> инженерный отчёт
```

Репозиторий задуман не как набор заметок, а как воспроизводимое учебно-инженерное пространство. В нём объединены документация, исполняемые лабораторные, HDL smoke-тесты, metadata для IQ-записей, шаблоны измерительных отчётов и структура итоговых проектов.

---

## Для кого этот курс

Курс полезен для:

- студентов, изучающих DSP, SDR и FPGA;
- инженеров, переходящих от MATLAB/Python-моделей к аппаратной реализации;
- FPGA-разработчиков, которым нужен прикладной проект по обработке сигналов;
- преподавателей, собирающих практический лабораторный трек по SDR/FPGA;
- ревьюеров и работодателей, оценивающих инженерный уровень DSP/FPGA-проекта.

---

## Чему учит курс

| Уровень | Инженерный результат |
|---|---|
| Теория сигналов | Дискретизация, полоса, aliasing, IQ-представление и основы модуляции |
| DSP-моделирование | FFT, FIR, окна, цифровое смешение, decimation и эталонные графики |
| Fixed-point | Масштабирование, разрядность, насыщение, ошибка квантования и риски реализации |
| HDL / FPGA | Потоковые DSP-блоки, Verilog testbench, задержка и сравнение RTL с моделью |
| Zynq + AD9363 | Настройка RF frontend, план усилений и дисциплина аппаратного эксперимента |
| TX/RX chains | DUC/DDC, loopback-метрики, детектирование пакетов и измерительный маршрут |
| Синхронизация | CFO, коррекция фазы и тайминга, EVM, BER и mini-link OFDM |
| IQ data engineering | Чтение CI16/CU8/CF32, metadata, dataset manifest и replay-проверки |
| Измерительная отчётность | SNR, EVM, BER, неопределённость, ограничения и инженерные выводы |

---

## Аппаратная база

Аппаратно-ориентированная часть курса построена вокруг:

- плат класса **Xilinx Zynq-7020**;
- RF-модулей **AD9363 / ADRV-compatible**;
- **RTL-SDR** как независимого приёмника-наблюдателя;
- контролируемых RF-трактов с аттенюацией, metadata и правилами безопасности.

При этом курс можно проходить и без железа: многие лабораторные имеют синтетические данные, воспроизводимые скрипты и CI-проверки.

---

## Структура репозитория

| Путь | Назначение |
|---|---|
| `docs/` | Сайт MkDocs, карты курса, отчёты, руководства и сгенерированные артефакты |
| `blocks/` | Исходные материалы блоков курса и реализации лабораторных |
| `hardware/` | Подобранные локальные наборы по платам и стартовые материалы для bring-up |
| `tools/` | Скрипты сборки, smoke-проверок и воспроизводимости |
| `templates/` | Шаблоны отчётов, IQ metadata, RF safety и итоговых проектов |
| `datasets/` | Dataset manifests и описания небольших наборов данных |
| `reports/` | Шаблоны FPGA и измерительных отчётов |
| `experiments/` | Машинно-проверяемые manifest-файлы экспериментов |

---

## Быстрый старт

```bash
git clone https://github.com/Lay007/zynq-sdr-course.git
cd zynq-sdr-course
python tools/tasks.py install
python tools/tasks.py docs
python tools/tasks.py labs
```

Полная локальная smoke-проверка:

```bash
python tools/tasks.py smoke
```

Локальная CI-проверка перед большим push:

```bash
python tools/run_local_ci.py
```

Полезные команды:

| Команда | Назначение |
|---|---|
| `python tools/tasks.py install` | Установить Python-зависимости |
| `python tools/tasks.py docs` | Собрать сайт MkDocs в строгом режиме |
| `python tools/tasks.py serve` | Запустить локальный просмотр документации |
| `python tools/tasks.py labs` | Запустить представительные Python-лабораторные |
| `python tools/tasks.py hdl` | Запустить Verilog smoke-тесты блока 5 |
| `python tools/tasks.py smoke` | Выполнить проверку docs + labs + HDL |
| `python tools/run_local_ci.py` | Выполнить lint + pytest + docs + labs + canonical HDL smoke |
| `python tools/run_local_ci.py --quick` | Выполнить lint + pytest + canonical HDL smoke |
| `python tools/tasks.py clean` | Удалить локальные сгенерированные артефакты |

Локальная стартовая аппаратная база:

- [`hardware/7020_ad936x_sdr/README.md`](hardware/7020_ad936x_sdr/README.md) - импортированный стартовый комплект для платы Zynq-7020 + AD936x.

---

## Рекомендуемый маршрут изучения

1. **Введение в SDR** — инструменты, сигналы и первые приёмные эксперименты.
2. **Сигналы и дискретизация** — спектр, aliasing, complex baseband и IQ.
3. **Основы DSP** — FFT, FIR, окна, цифровое смешение и decimation.
4. **Fixed-point workflow** — числовые форматы, масштабирование и квантование.
5. **FPGA / HDL flow** — потоковые интерфейсы, Verilog и testbench.
6. **RF frontend** — частотный план, усиления и настройки AD9363.
7. **TX/RX chains** — DUC, DDC, loopback и packet-level метрики.
8. **Синхронизация** — CFO, фаза, тайминг, EVM и BER.
9. **Запись и анализ IQ** — metadata, форматы, replay и контроль качества.
10. **Электроника и KiCad** — аттенюаторы, фильтры и RF safety.
11. **Интегрированный SDR-проект** — модель, реализация, запись и отчёт.
12. **Итоговые проекты** — portfolio-ready инженерные результаты.

---

## Ключевые страницы документации

| Страница | Зачем открыть |
|---|---|
| [Course demo dashboard](docs/demo-dashboard.md) | Быстрый визуальный обзор исполняемых артефактов курса |
| [Visual course map](docs/course-map.md) | Полный маршрут от теории до итогового проекта |
| [Student path](docs/student-path.md) | Самый короткий путь для студента |
| [Reviewer path](docs/reviewer-path.md) | Маршрут для быстрой оценки зрелости репозитория |
| [Instructor guide](docs/instructor-guide.md) | Как использовать репозиторий как учебное пространство |
| [Model → FPGA → RF → Measurement](docs/model-to-measurement.md) | Главный инженерный маршрут курса |
| [Course status](docs/status.md) | Матрица готовности, пробелы и следующие улучшения |
| [Reproducibility guide](docs/reproducibility-guide.md) | Как пересобрать результаты и артефакты |
| [Real data policy](docs/real-data-policy.md) | Как работать с IQ-записями без раздувания репозитория |

---

## Инженерная философия

Главная идея курса:

```text
Модель -> Реализация -> Измерение -> Решение
```

Результат считается зрелым только тогда, когда он связан с доказательствами: сгенерированными графиками, метриками, HDL-симуляцией, metadata набора данных, RF safety notes или воспроизводимым инженерным отчётом.

---

## Текущий фокус зрелости

В репозитории уже есть:

- двуязычная документация MkDocs;
- исполняемые лабораторные по DSP и синхронизации;
- HDL smoke-проверки для FPGA-ориентированных примеров;
- workflow для записи и анализа IQ;
- manifest-файлы экспериментов;
- шаблоны отчётов и структура итогового проекта.

Следующие важные proof points:

- валидированные аппаратные захваты Zynq/AD9363;
- небольшие публичные или внешне размещённые IQ demo datasets;
- routed top-level Vivado implementation reports для интегрированного Zynq-дизайна;
- полный QPSK или tone model-to-measurement отчёт.

---

## Ценность как portfolio-проекта

Репозиторий демонстрирует практическую компетенцию в:

- проектировании DSP-алгоритмов;
- fixed-point мышлении;
- FPGA/HDL верификации;
- архитектуре SDR-систем;
- дисциплине RF-измерений;
- воспроизводимой инженерной документации;
- CI-assisted учебном workflow.

---

## Лицензия

MIT License. См. [LICENSE].
