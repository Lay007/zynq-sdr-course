# Zynq SDR Course / Курс SDR на Zynq

[![Bilingual](https://img.shields.io/badge/language-RU%20%2F%20EN-blueviolet)](#)
[![MkDocs](https://img.shields.io/badge/site-MkDocs%20Material-informational)](#)
[![Pages](https://github.com/Lay007/zynq-sdr-course/actions/workflows/pages.yml/badge.svg)](https://github.com/Lay007/zynq-sdr-course/actions/workflows/pages.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A **bilingual engineering course on SDR** that connects signal theory, DSP, fixed-point modeling, FPGA flow, RF front-end understanding, and board-level implementation.

Это **двуязычный инженерный курс по SDR**, который связывает теорию сигналов, DSP, fixed-point моделирование, FPGA flow, понимание радиотракта и практическую реализацию на плате.

## Navigation / Навигация

- [Русская версия / Russian version](README_ru.md)
- [English version / Английская версия](README_en.md)

## Why this repository matters / Почему этот репозиторий важен

This repository is not just a collection of markdown notes. It is structured as a **teaching and implementation path** from first SDR concepts to hardware-oriented project work.

Этот репозиторий — не просто набор markdown-файлов. Он оформлен как **учебный и инженерный маршрут** от первых понятий SDR до проектной работы, ориентированной на железо.

It is designed for learners and practitioners who want to move through a coherent chain:

Он рассчитан на тех, кто хочет пройти связную цепочку:

**theory → modeling → fixed-point → HDL / FPGA → SDR board → external reception → IQ recording → analysis → circuit design → final project**

**теория → моделирование → fixed-point → HDL / FPGA → SDR-плата → внешний приём → запись IQ → анализ → схемотехника → итоговый проект**

## Course website / Сайт курса

The repository already includes an **MkDocs Material** site configuration and a **GitHub Pages deployment workflow**.

В репозитории уже есть конфигурация сайта на **MkDocs Material** и workflow для публикации через **GitHub Pages**.

Configured site URL / Настроенный адрес сайта:

- `https://lay007.github.io/zynq-sdr-course/`

## Current state / Текущее состояние

- **Block 1 is fully populated in bilingual form** / **Блок 1 полностью наполнен в двуязычном формате**
- **The remaining blocks already have structured bilingual scaffolds** / **Остальные блоки уже имеют структурированные двуязычные каркасы**
- **The repository is ready for iterative course development and site publication** / **Репозиторий готов к поэтапному развитию курса и публикации в виде сайта**

## Hardware baseline / Аппаратная база

The current hands-on setup already includes a simple external receiver and a board-level SDR platform for practical experiments.

Текущая практическая аппаратная база уже включает простой внешний приёмник и SDR-платформу на уровне платы для лабораторных работ и экспериментов.

### RTL-SDR V3 Pro / RTL-SDR V3 Pro

![RTL-SDR V3 Pro](docs/images/hardware/rtl_sdr_v3_pro.svg)

The RTL-SDR dongle is used as an accessible external receiver for the first reception, capture, and observation tasks.

RTL-SDR используется как доступный внешний приёмник для первых задач по приёму, записи и наблюдению сигнала.

### Xilinx Zynq-7020 + ADRV module / Плата Xilinx Zynq-7020 + модуль ADRV

Photos of the Zynq-7020 board with the ADRV RF module are being added as part of the hardware-oriented expansion of the course.

Фотографии платы Zynq-7020 с RF-модулем ADRV добавляются в рамках усиления аппаратно-ориентированной части курса.

## Course blocks / Блоки курса

1. `blocks/block_01_intro_sdr` — introduction, tools, and first signal reception / введение, инструменты и первый приём сигнала
2. `blocks/block_02_signals_and_sampling` — signals, spectrum, sampling, IQ / сигналы, спектр, дискретизация, IQ
3. `blocks/block_03_dsp_basics` — FFT, filtering, windows, basic DSP operations / FFT, фильтрация, окна, базовые DSP-операции
4. `blocks/block_04_simulink_and_fixed_point` — modeling, fixed-point, and hardware preparation / моделирование, fixed-point и подготовка к железу
5. `blocks/block_05_fpga_hdl_flow` — Simulink, HDL, Vivado, and SoC flow / маршрут Simulink, HDL, Vivado и SoC
6. `blocks/block_06_rf_frontend_and_ad9363` — RF chain, levels, frequencies, AD9363 / радиотракт, уровни, частоты, AD9363
7. `blocks/block_07_tx_rx_chains` — TX/RX chains, DUC, DDC / тракты TX/RX, DUC, DDC
8. `blocks/block_08_modulation_and_synchronization` — modulation, demodulation, synchronization / модуляция, демодуляция, синхронизация
9. `blocks/block_09_recording_and_analysis_tools` — HDSDR, GNU Radio, MATLAB, Python, C++ / HDSDR, GNU Radio, MATLAB, Python, C++
10. `blocks/block_10_kicad_and_basic_electronics` — KiCad, breadboard, analog and digital support circuits / KiCad, макетная плата, аналоговые и цифровые вспомогательные узлы
11. `blocks/block_11_integrated_sdr_project` — integrated educational SDR project / интегрированный учебный SDR-проект
12. `blocks/block_12_final_projects` — final project work / итоговые проектные работы

## Core repository guides / Основные материалы навигации

- [Course structure / Структура курса](COURSE_STRUCTURE_en.md)
- [Lab track / Лабораторный трек](LAB_TRACK_en.md)
- [Media guide / Медиа-гайд](MEDIA_GUIDE_en.md)
- [Структура курса / Course structure](COURSE_STRUCTURE_ru.md)
- [Лабораторный трек / Lab track](LAB_TRACK_ru.md)
- [Медиа-гайд / Media guide](MEDIA_GUIDE_ru.md)

## What makes the course stronger / Что делает курс сильнее

- bilingual parallel presentation instead of mixed-language notes
- an explicit bridge from theory to board-level implementation
- integration of DSP, Simulink, FPGA flow, RF understanding, and electronics
- a repository structure suitable for both reading on GitHub and publishing as a documentation site

- параллельная двуязычная подача вместо смешанных заметок
- явный мостик от теории к реализации на плате
- объединение DSP, Simulink, FPGA flow, понимания радиотракта и электроники
- структура репозитория, удобная и для чтения на GitHub, и для публикации как сайта документации

## Recommended next development steps / Рекомендуемые следующие шаги

- continue filling Blocks 2–12 in the same bilingual style
- add illustrations, schematics, and board photos to the most hardware-oriented modules
- enrich labs with recordings, IQ examples, and analysis notebooks or scripts
- connect the course materials with more integrated end-to-end practical projects

- последовательно наполнять блоки 2–12 в том же двуязычном стиле
- добавить иллюстрации, схемы и фото плат в аппаратно-ориентированные разделы
- расширить лабораторные работы записями, IQ-примерами и скриптами анализа
- усиливать курс интегрированными практическими проектами полного цикла

## License / Лицензия

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

Проект распространяется по лицензии MIT. Подробности см. в файле [LICENSE](LICENSE).
