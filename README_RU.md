# Курс SDR на Zynq

[![MkDocs](https://img.shields.io/badge/site-MkDocs%20Material-informational)](https://lay007.github.io/zynq-sdr-course/)
[![Wiki](https://img.shields.io/badge/engineering-Wiki-informational)](https://github.com/Lay007/zynq-sdr-course/wiki)
[![Discussions](https://img.shields.io/badge/community-Discussions-blue)](https://github.com/Lay007/zynq-sdr-course/discussions)
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

## С чего начать

| Задача | Куда перейти |
| --- | --- |
| Последовательно изучить курс | [Сайт курса](https://lay007.github.io/zynq-sdr-course/), [маршрут студента](docs/student-path.md) |
| Установить инструменты и выбрать аппаратную базу | [Маршруты обучения](LAB_TRACK_ru.md), [Getting Started Wiki](https://github.com/Lay007/zynq-sdr-course/wiki/Getting-Started) |
| Разобраться с переходом от DSP-модели к FPGA и радиотракту | [Architecture Wiki](https://github.com/Lay007/zynq-sdr-course/wiki/Architecture), [DSP to FPGA](https://github.com/Lay007/zynq-sdr-course/wiki/DSP-to-FPGA) |
| Запустить Zynq/AD936x или найти причину ошибки | [Hardware Wiki](https://github.com/Lay007/zynq-sdr-course/wiki/Hardware), [Troubleshooting](https://github.com/Lay007/zynq-sdr-course/wiki/Troubleshooting) |
| Посмотреть подтверждённые результаты | [Путь для ревью](docs/reviewer-path.md), [индекс измерений](docs/hardware-evidence-index.md) |
| Преподавать курс или добавить лабораторную | [Руководство преподавателя](docs/instructor-guide.md), [Contributing](CONTRIBUTING.md) |
| Задать вопрос или предложить улучшение | [FAQ](https://github.com/Lay007/zynq-sdr-course/wiki/FAQ), [Поддержка](SUPPORT.md), [Как помочь](CONTRIBUTING.md) |

**О результатах:** моделирование, RTL-тест, проверка на FPGA и RF-измерение подтверждают разные вещи. Для численных результатов ориентируйтесь на отчёт и его ограничения.

---

## Обзор

`zynq-sdr-course` это инженерный курс по SDR, построенный вокруг полного маршрута от модели до измерения:

```text
теория -> DSP-модель -> fixed-point -> HDL/FPGA -> Zynq/AD9363 -> RF-тракт -> запись IQ -> анализ -> инженерный отчёт
```

Репозиторий задуман не как набор заметок, а как воспроизводимое учебно-инженерное пространство. В нём объединены документация, исполняемые лабораторные, HDL smoke-тесты, metadata для IQ-записей, шаблоны измерительных отчётов и структура итоговых проектов.

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
- RF-модулей **AD9363 / AD9361** с проверкой конкретной платы и образа;
- **RTL-SDR** как независимого приёмника-наблюдателя;
- контролируемых RF-трактов с аттенюацией, metadata и правилами безопасности.

При этом курс можно проходить и без железа: многие лабораторные имеют синтетические данные, воспроизводимые скрипты и CI-проверки.

### Связанные репозитории

- C++-ядра DSP, численные тесты, сборка CMake и воспроизводимые замеры производительности:
  **[cpp-dsp-showcase](https://github.com/Lay007/cpp-dsp-showcase)**.
- Следующий шаг после CSS/LoRa-like лабораторных блока 8:
  **[zynq-lora-phy](https://github.com/Lay007/zynq-lora-phy)**,
  отдельный SDR-проект на Zynq по реализации LoRa PHY, синхронизации,
  измерениям PER на железе и исследованию позиционирования.
- Опубликованные bitstream, загрузочные наборы и резервные копии плат находятся
  в приватном репозитории `zynq-sdr-course-artifacts`. В исходном репозитории
  остаются manifest-файлы, измерения и инструкции по воспроизведению, но не
  крупные или привязанные к конкретной плате бинарные файлы.

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
| `reports/` | FPGA-отчёты, примеры измерительных отчётов и карта доказательств для ревьюера |
| `experiments/` | Машинно-проверяемые manifest-файлы экспериментов |

---

## Что нужно

| Что | Для чего | Замечания |
|---|---|---|
| Python 3.12 или новее | для всего | CI работает на Python 3.12 под Ubuntu; курс используется и на Windows 11 с Python 3.14. Версии пакетов закреплены в `requirements.txt`. |
| Git LFS | записанные IQ и наборы данных | `git lfs install`, затем `git lfs pull`. Без него вместо записей лежат маленькие текстовые файлы-указатели. |
| Icarus Verilog 12 (`iverilog`, `vvp`) | все HDL-стенды (`tasks.py hdl`, `tools/run_ofdm_rtl.py`) | Для Python-лабораторных не нужен. |
| Vivado 2021.1 | out-of-context отчёты и образы для плат (блоки 5, 8, 11) | Для симуляции не нужен. Образы для плат собирает `hardware/7020_ad936x_sdr/rebuild_vendor_xpr_snapshot_course_overlay.tcl`. |
| MATLAB / Simulink | необязательные модели `.slx` блока 4 | Python покрывает базовый маршрут; запуск моделей `.slx` требует MATLAB/Simulink и указанных в лабораторной toolbox. |
| RTL-SDR, затем плата Zynq-7020 + AD9363/AD9361 | аппаратные маршруты | Начинать можно без них: [маршруты обучения](LAB_TRACK_ru.md) от A (только ноутбук) до D (стендовые приборы). |

## Быстрый старт

```bash
git clone https://github.com/Lay007/zynq-sdr-course.git
cd zynq-sdr-course
python tools/tasks.py install
python tools/tasks.py docs
python tools/tasks.py labs
```

Признак успеха: MkDocs завершает строгую сборку, а все 20 представительных лабораторных выдают `PASS`. В конце названы файлы сводки в `docs/assets/`. Время зависит от компьютера. Строгая сборка проверяет настроенные предупреждения документации; доступность внешних URL она не проверяет.

Полная локальная smoke-проверка:

```bash
python tools/tasks.py smoke
```

Локальная CI-проверка перед большим push:

```bash
python tools/tasks.py install-dev
python tools/run_local_ci.py
```

Полезные команды:

| Команда | Назначение |
|---|---|
| `python tools/tasks.py install` | Установить Python-зависимости |
| `python tools/tasks.py install-dev` | Установить runtime-, lint- и test-зависимости |
| `python tools/tasks.py docs` | Собрать сайт MkDocs в строгом режиме |
| `python tools/tasks.py serve` | Запустить локальный просмотр документации |
| `python tools/tasks.py labs` | Запустить представительные Python-лабораторные |
| `python tools/tasks.py hdl` | Запустить Verilog-регрессии блоков 5 и 8 CSS |
| `python tools/tasks.py smoke` | Выполнить проверку docs + labs + HDL |
| `python tools/run_local_ci.py` | Выполнить lint + pytest + docs + labs + canonical HDL smoke |
| `python tools/run_local_ci.py --quick` | Выполнить lint + pytest + canonical HDL smoke |
| `python tools/check_lab_id_registry.py` | Проверить владельцев ID поздних лабораторных Block 11 |
| `python tools/check_dataset_manifests.py` | Проверить dataset manifests и SHA256 в Git LFS pointer-файлах |
| `python tools/tasks.py clean` | Удалить локальные сгенерированные артефакты |

Локальная стартовая аппаратная база:

- [`hardware/7020_ad936x_sdr/README.md`](hardware/7020_ad936x_sdr/README.md): импортированный стартовый комплект для платы Zynq-7020 + AD936x.

OFDM-стенды не входят в `tasks.py hdl`: их запускает `python tools/run_ofdm_rtl.py` (последняя строка: `OFDM RTL (...): N testbenches and M parameter variant(s) passed`).

## Частые проблемы

| Признак | Причина и что делать |
|---|---|
| Не найден `iverilog` или `vvp` | Установить Icarus Verilog и добавить его в `PATH`; нужен только HDL-проверкам. |
| Лабораторная, читающая запись, падает на формате файла, или файл весит несколько сотен байт | Это указатель Git LFS, а не запись: `git lfs install && git lfs pull`. |
| `mkdocs build --strict` останавливается с предупреждением | Страница ссылается на несуществующий файл или якорь; предупреждение называет оба. |
| Vivado падает с `couldn't read file ... No error` или во время синтеза | Проверить первую ошибку и расход памяти. На стенде курса параллельные сборки приводили к нехватке памяти; повторить одну сборку с `-jobs 1` и сохранить журнал. |
| Русская страница выглядит испорченной в консоли Windows | Файлы в UTF-8; читать их через `Get-Content -Encoding utf8` или в редакторе. |
| Проблемы на плате (нет передачи, несущая между пачками, AD9361 перестаёт работать после загрузки битстрима на ходу) | См. [указатель аппаратных доказательств](docs/hardware-evidence-index.md) и лабораторные блока 11; у каждой встреченной на стенде проблемы своя страница. |

---

## Рекомендуемый маршрут изучения

1. **Введение в SDR**: инструменты, сигналы и первые приёмные эксперименты.
2. **Сигналы и дискретизация**: спектр, aliasing, complex baseband и IQ.
3. **Основы DSP**: FFT, FIR, окна, цифровое смешение и decimation.
4. **Fixed-point workflow**: числовые форматы, масштабирование и квантование.
5. **FPGA / HDL flow**: потоковые интерфейсы, Verilog и testbench.
6. **RF frontend**: частотный план, усиления и настройки AD9363.
7. **TX/RX chains**: DUC, DDC, loopback и packet-level метрики.
8. **Синхронизация**: CFO, фаза, тайминг, EVM и BER.
9. **Запись и анализ IQ**: metadata, форматы, replay и контроль качества.
10. **Электроника и KiCad**: аттенюаторы, фильтры и RF safety.
11. **Интегрированный SDR-проект**: модель, реализация, запись и отчёт.
12. **Итоговые проекты**: собственный проект, от предложения до отчёта с измерениями.

Какие лабораторные требуют какого оборудования и в каком порядке их проходить: [маршруты обучения](LAB_TRACK_ru.md).

---

## Сообщество и план развития

- **[Discussions](https://github.com/Lay007/zynq-sdr-course/discussions):** вопросы по лабораторным работам, DSP, fixed-point, HDL, SDR, предложения и результаты экспериментов.
- **[Issues](https://github.com/Lay007/zynq-sdr-course/issues):** воспроизводимые ошибки и конкретные инженерные задачи.
- **[Roadmap проекта](https://github.com/users/Lay007/projects/1):** открытые инженерные задачи, ход разработки и этапы проверки. В доске используются существующие GitHub Issues; настройка сообщества отслеживается в [#77](https://github.com/Lay007/zynq-sdr-course/issues/77).
- **[Support](SUPPORT.md):** как выбрать правильное место для вопроса или сообщения об ошибке.

[Wiki](https://github.com/Lay007/zynq-sdr-course/wiki) служит кратким справочником, а [сайт курса](https://lay007.github.io/zynq-sdr-course/) остаётся основным источником лабораторных работ и подтверждённых результатов.

Сопровождающие редактируют [отслеживаемые исходники Wiki](wiki/README.md) и публикуют их отдельно после ревью. Текущее состояние GitHub описано в [памятке по сообществу](COMMUNITY_PLAYBOOK.md).

---

## Ключевые страницы документации

| Страница | Зачем открыть |
|---|---|
| [Course demo dashboard](docs/demo-dashboard.md) | Быстрый визуальный обзор исполняемых артефактов курса |
| [Visual course map](docs/course-map.md) | Полный маршрут от теории до итогового проекта |
| [Student path](docs/student-path.md) | Самый короткий путь для студента |
| [Reviewer path](docs/reviewer-path.md) | Маршрут для быстрой оценки зрелости репозитория |
| [Reviewer acceptance checklist](docs/reviewer-checklist.md) | Pass/fail checklist для воспроизводимости, DSP, HDL, RF и итоговых проектов |
| [Course evidence map](reports/course-evidence-map.md) | Краткая карта доказанных артефактов, пробелов и следующих действий |
| [Instructor guide](docs/instructor-guide.md) | Как использовать репозиторий как учебное пространство |
| [Model → FPGA → RF → Measurement](docs/model-to-measurement.md) | Главный инженерный маршрут курса |
| [Course status](docs/status.md) | Матрица готовности, пробелы и следующие улучшения |
| [Reproducibility guide](docs/reproducibility-guide.md) | Как пересобрать результаты и артефакты |
| [Real data policy](docs/real-data-policy.md) | Как работать с IQ-записями без раздувания репозитория |
| [Маршруты обучения](LAB_TRACK_ru.md) | Маршруты A-D: только ноутбук, + RTL-SDR, + плата Zynq, + стендовые приборы |
| [Как написать лабораторную](docs/contributing-labs.md) | Структура страницы, проверки и соглашения для новых лабораторных |

---

## Проверенные результаты и ограничения

Уровень доказательств относится к конкретному эксперименту и образу. Эти отчёты описывают ранее выполненные измерения; локальные Python/RTL-проверки их не повторяют.

| Компонент | Доступные доказательства | Ограничение |
| --- | --- | --- |
| DSP и fixed-point | Детерминированные модели и [регрессии](docs/ci-matrix.md) | Проверка модели не подтверждает FPGA или RF |
| QPSK на двух платах | [Итоговый отчёт Lab 11.4](blocks/block_11_integrated_sdr_project/lab_11_4_final_measurement_report.md): 915 МГц, ноль разворотов целого бёрста, payload BER около 4×10⁻⁴ | Результат конкретной конфигурации; остаточные ошибки DC blocker отслеживает [#66](https://github.com/Lay007/zynq-sdr-course/issues/66) |
| Mailbox и чат | [Измерения link layer](reports/hardware/two-board-link-layer-20261017.md), Labs 11.49-11.52 | Новый RX_STOP из [#71](https://github.com/Lay007/zynq-sdr-course/issues/71) ещё требует проверки на платах |
| OFDM | [Петля через AXI DMA внутри FPGA](reports/hardware/ofdm-dma-fabric-loopback-20261014.md): 0 ошибок на 3 072 000 бит | Радиочасть проверена в симуляции и собрана; RF-валидация [#48](https://github.com/Lay007/zynq-sdr-course/issues/48) открыта |
| IQ-наборы | [Манифесты](docs/iq-dataset-manifest.md) и [правила данных](docs/real-data-policy.md) отделяют измеренные записи от синтетического QPSK replay | Часть сырых измеренных записей и образов недоступна публично |

Дальнейшие задачи включают RF-проверку OFDM, RX_STOP на платах, калибровку RF-тракта и устойчивость тайминга повторных сборок. См. [статус курса](docs/status.md), [указатель аппаратных доказательств](docs/hardware-evidence-index.md) и [инженерный аудит от 2026-10-28](reports/repository-review-2026-10-28.md).

---

## Автор

Alexander Lyubko. Вопросы по курсу, а также R&D-работы по SDR, DSP, fixed-point, переходу
от MATLAB/Simulink к RTL и интеграции Zynq/AD936x: [инженерное портфолио](https://lay007.github.io/),
[GitHub](https://github.com/Lay007), [LinkedIn](https://ru.linkedin.com/in/alexander-lyubko-dsp).

---

## Лицензия

MIT License. См. [LICENSE](LICENSE).
