# Курс SDR на Zynq: от теории к реализации на плате

[![Bilingual](https://img.shields.io/badge/language-RU%20%2F%20EN-blueviolet)](#)
[![MkDocs](https://img.shields.io/badge/site-MkDocs%20Material-informational)](mkdocs.yml)
[![Pages](https://github.com/Lay007/zynq-sdr-course/actions/workflows/pages.yml/badge.svg)](https://github.com/Lay007/zynq-sdr-course/actions/workflows/pages.yml)
[![Full Course Smoke](https://github.com/Lay007/zynq-sdr-course/actions/workflows/full_course_smoke.yml/badge.svg)](https://github.com/Lay007/zynq-sdr-course/actions/workflows/full_course_smoke.yml)
[![Block 5 HDL](https://github.com/Lay007/zynq-sdr-course/actions/workflows/block5_hdl.yml/badge.svg)](https://github.com/Lay007/zynq-sdr-course/actions/workflows/block5_hdl.yml)
[![Block 8 Sync](https://github.com/Lay007/zynq-sdr-course/actions/workflows/block8_sync.yml/badge.svg)](https://github.com/Lay007/zynq-sdr-course/actions/workflows/block8_sync.yml)
[![Block 9 Recording](https://github.com/Lay007/zynq-sdr-course/actions/workflows/block9_recording_analysis.yml/badge.svg)](https://github.com/Lay007/zynq-sdr-course/actions/workflows/block9_recording_analysis.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Это **двуязычный инженерный курс по Software-Defined Radio**, который связывает теорию, моделирование, fixed-point DSP, HDL/FPGA-реализацию, радиотракт, запись IQ, измерения и итоговые инженерные отчёты.

Репозиторий построен как сквозной маршрут, а не как разрозненный набор заметок:

```text
теория -> моделирование -> fixed-point -> HDL/FPGA -> Zynq/AD9363 -> RF-тракт -> внешний приёмник -> запись IQ -> анализ -> электроника -> итоговый проект
```

## Веб-версия курса

- Опубликованная документация: <https://lay007.github.io/zynq-sdr-course/>
- Двуязычная landing page: [README.md](README.md)
- English version: [README_en.md](README_en.md)

## Быстрый старт за 10 минут

```bash
git clone https://github.com/Lay007/zynq-sdr-course.git
cd zynq-sdr-course
python tools/tasks.py install
python tools/tasks.py docs
python tools/tasks.py labs
```

Для полной локальной smoke-проверки установите Icarus Verilog (`iverilog`) и выполните:

```bash
python tools/tasks.py smoke
```

| Команда | Назначение |
|---|---|
| `python tools/tasks.py install` | Установить Python-зависимости |
| `python tools/tasks.py docs` | Собрать сайт MkDocs в строгом режиме |
| `python tools/tasks.py serve` | Запустить локальный предпросмотр сайта |
| `python tools/tasks.py labs` | Запустить представительные исполняемые Python-лабораторные |
| `python tools/tasks.py hdl` | Запустить smoke-тесты Verilog для блока 5 |
| `python tools/tasks.py smoke` | Выполнить проверку docs + labs + HDL |
| `python tools/tasks.py clean` | Удалить локальные сгенерированные артефакты |

## Быстрая навигация

| Страница | Зачем открыть |
|---|---|
| [Course demo dashboard](docs/demo-dashboard.md) | Быстрый визуальный обзор сгенерированных артефактов курса |
| [Visual course map](docs/course-map.md) | Полный маршрут от теории до итогового проекта |
| [Course status](docs/status.md) | Краткая инженерная сводка по готовности блоков, лабораторных и аппаратной части |
| [Student path](docs/student-path.md) | Самый короткий учебный маршрут по репозиторию |
| [Reviewer path](docs/reviewer-path.md) | Быстрый маршрут для оценки зрелости и доказательной базы |
| [Instructor guide](docs/instructor-guide.md) | Как использовать репозиторий как учебное пространство |
| [Model → FPGA → RF → Measurement](docs/model-to-measurement.md) | Главный системный мост курса: модель, FPGA, радиотракт и измерения |
| [Hardware checklist](docs/hardware-checklist.md) | Одна страница для входа в bring-up, RF safety и правила отчётности |
| [Hardware experiment roadmap](docs/hardware-experiment-roadmap.md) | Практический путь от запуска платы до RF-наблюдений |
| [Lab index](docs/lab-index.md) | Все лабораторные и демонстрационные страницы в одном месте |
| [Reproducibility guide](docs/reproducibility-guide.md) | Как пересобрать результаты и сгенерированные артефакты |
| [Real data policy](docs/real-data-policy.md) | Как хранить, описывать и подключать IQ-записи |
| [Portfolio view](docs/portfolio-view.md) | Что репозиторий демонстрирует как инженерный portfolio-проект |

## Чему учит курс

| Слой | Инженерный результат |
|---|---|
| Сигналы и спектры | Дискретизация, полоса, aliasing, комплексная baseband-модель и основы модуляции |
| DSP-моделирование | FFT, FIR, окна, цифровое смешение, decimation и эталонные графики |
| Fixed-point DSP | Разрядность, масштабирование, ошибка квантования и компромиссы реализации |
| HDL / FPGA | Потоковые DSP-блоки, Verilog testbench, задержка и сравнение RTL с моделью |
| Zynq + AD9363 | Настройка RF, план частот/усилений и эксперименты на уровне платы |
| TX/RX chains | DUC/DDC, loopback-метрики, детектирование пакетов и измерительный маршрут |
| Синхронизация | CFO, коррекция фазы/тайминга, EVM, BER и mini-link OFDM |
| Запись IQ | Чтение CI16/CU8/CF32, metadata, контроль качества записи и replay |
| Электроника / KiCad | Аттенюаторы, RC-фильтры, RF-безопасность и дисциплина схемотехники |
| Итоговый проект | Требования, архитектура, измерительный отчёт и результат уровня портфолио |

## Структура репозитория

| Путь | Роль |
|---|---|
| `docs/` | Сайт MkDocs, двуязычные страницы, сгенерированные артефакты и графики |
| `blocks/` | Исходные блоки курса и материалы лабораторных работ |
| `tools/` | Скрипты воспроизводимости, сборки и запуска лабораторных |
| `templates/` | Шаблоны отчётов, metadata IQ-записей, RF safety и итоговых документов |
| `COURSE_STRUCTURE_ru.md` | Русскоязычная структура курса |
| `LAB_TRACK_ru.md` | Русскоязычная лабораторная траектория |
| `MEDIA_GUIDE_ru.md` | Руководство по фото, схемам, анимации и сгенерированным визуальным материалам |

## Аппаратная база

Практическая часть курса сочетает доступный независимый приёмник и SDR-платформу уровня платы. Это позволяет наблюдать первые RF-эксперименты ещё до глубокого погружения в FPGA и радиотракт.

### RTL-SDR V3 Pro

![RTL-SDR V3 Pro](docs/images/hardware/rtl_sdr_v3_pro_real.png)

RTL-SDR используется как внешний приёмник-наблюдатель для первых задач приёма, просмотра спектра, waterfall-наблюдения и записи IQ.

### Xilinx Zynq-7020 + AD9363/ADRV module

![Xilinx Zynq-7020 with ADRV module](docs/images/hardware/xilinx_7020_adrv_real.png)

SDR-плата на базе Zynq — целевая платформа аппаратно-ориентированной части курса: модельная генерация сигналов, FPGA/SoC-интеграция, настройка RF и измерения.

### SDR-стенд

![SDR training stand diagram](docs/images/hardware/sdr_stand_diagram.svg)

Практический поток: **смоделировать сигнал → настроить платформу Zynq/AD9363 → передать или провести сигнал через контролируемый RF-путь → принять его через RTL-SDR → наблюдать в HDSDR → записать IQ → проанализировать запись в MATLAB, Python, C++ или GNU Radio**.

## Блоки курса

1. [`blocks/block_01_intro_sdr`](blocks/block_01_intro_sdr) — введение, инструменты и первый приём сигнала
2. [`blocks/block_02_signals_and_sampling`](blocks/block_02_signals_and_sampling) — сигналы, спектр, дискретизация и IQ
3. [`blocks/block_03_dsp_basics`](blocks/block_03_dsp_basics) — FFT, фильтрация, окна и базовые DSP-операции
4. [`blocks/block_04_simulink_and_fixed_point`](blocks/block_04_simulink_and_fixed_point) — моделирование, fixed-point и подготовка к железу
5. [`blocks/block_05_fpga_hdl_flow`](blocks/block_05_fpga_hdl_flow) — Simulink, HDL, Vivado, SoC и testbench
6. [`blocks/block_06_rf_frontend_and_ad9363`](blocks/block_06_rf_frontend_and_ad9363) — радиотракт, уровни, частотное планирование и AD9363
7. [`blocks/block_07_tx_rx_chains`](blocks/block_07_tx_rx_chains) — тракты передачи/приёма, DUC, DDC и loopback-метрики
8. [`blocks/block_08_modulation_and_synchronization`](blocks/block_08_modulation_and_synchronization) — модуляция, демодуляция, синхронизация, BER и EVM
9. [`blocks/block_09_recording_and_analysis_tools`](blocks/block_09_recording_and_analysis_tools) — HDSDR, GNU Radio, MATLAB, Python и C++ анализ
10. [`blocks/block_10_kicad_and_basic_electronics`](blocks/block_10_kicad_and_basic_electronics) — KiCad, макетная плата, аттенюаторы, фильтры и RF safety
11. [`blocks/block_11_integrated_sdr_project`](blocks/block_11_integrated_sdr_project) — интегрированный учебный SDR-проект
12. [`blocks/block_12_final_projects`](blocks/block_12_final_projects) — итоговые проекты и инженерный отчёт

## Текущее инженерное состояние

- В курсе есть двуязычная структура MkDocs с русской и английской навигацией.
- Блок 1 полностью наполнен, последующие блоки оформлены как структурированные учебные модули.
- Блоки 3–11 уже содержат исполняемые или измерительно-ориентированные лабораторные страницы на сайте документации.
- CI workflow проверяют публикацию MkDocs, full-course smoke, HDL-тесты, синхронизацию и запись/анализ IQ.
- Сгенерированные IEEE-style графики и отчёты воспроизводимости хранятся в `docs/assets`.

## Почему этот репозиторий сильный

- Он показывает полный инженерный маршрут, а не только теорию SDR.
- Он связывает MATLAB/Simulink-подход, fixed-point, HDL, RF и измерения.
- Он использует реальный аппаратный контекст: Zynq-7020, AD9363/ADRV, RTL-SDR и HDSDR.
- Он полезен и как учебный курс, и как инженерный portfolio-репозиторий.
- Он ориентирован на воспроизводимость: в проекте есть скрипты, шаблоны, CI workflow и сгенерированные графики.

## Рекомендуемые следующие улучшения

1. Добавить небольшие проверенные public IQ demo-файлы или dataset manifest, не раздувая репозиторий крупными записями.
2. Добавить board-level validation package для AD9363/Zynq: частотный план, gain table, измерения и короткий reproducible report.
3. Добавить measured photos и экспортированные KiCad-артефакты для блока 10, чтобы электроника была не только текстовой.
4. Связать больше лабораторных с явной таблицей Block → Lab → Artifact → CI check.
5. Усилить один end-to-end hardware case как главный reviewer demo с фиксированным набором артефактов.

## Лицензия

Проект распространяется по лицензии MIT. Подробности см. в [LICENSE](LICENSE).
