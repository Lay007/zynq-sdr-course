# Zynq SDR Course / Курс SDR на Zynq

[![Bilingual](https://img.shields.io/badge/language-RU%20%2F%20EN-blueviolet)](#)
[![MkDocs](https://img.shields.io/badge/site-MkDocs%20Material-informational)](#)
[![IEEE-style plots](https://img.shields.io/badge/plots-IEEE--style%20auto--generated-success)](.github/workflows/generate_plots.yml)
[![Pages deploy](https://img.shields.io/badge/pages-deploy%20manual-lightgrey)](.github/workflows/pages.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A **bilingual engineering course on SDR** that connects signal theory, DSP, fixed-point modeling, HDL/FPGA flow, RF front-end understanding, board-level experiments, measurements, and engineering reports.

Это **двуязычный инженерный курс по SDR**, который связывает теорию сигналов, DSP, fixed-point моделирование, HDL/FPGA flow, понимание радиотракта, практическую работу с платой, измерения и инженерные отчёты.

![Zynq SDR Course Pipeline](docs/assets/course_pipeline.svg)

## What this course teaches / Чему учит курс

| Layer | Engineering result |
|---|---|
| **Signals and spectra** | sampling, bandwidth, aliasing, modulation basics |
| **MATLAB / Simulink modeling** | reference waveforms, plots, repeatable experiments |
| **Fixed-point DSP** | word length, scaling, quantization, implementation error |
| **HDL / FPGA** | Verilog blocks, streaming DSP, latency, testbenches |
| **Zynq + AD9363 hardware** | RF configuration, board-level signal generation and capture |
| **External measurement** | RTL-SDR, HDSDR, IQ recording, independent observation |
| **Analysis and reports** | FFT, EVM, BER, SNR, engineering conclusions |

## Quick navigation / Быстрая навигация

- [Русская версия / Russian version](README_ru.md)
- [English version / Английская версия](README_en.md)
- [IEEE-style guide](docs/ieee_style_guide.md)
- [GitHub demo notes](docs/demo_readme.md)
- [Course blocks](#course-blocks--блоки-курса)
- [Hardware baseline](#hardware-baseline--аппаратная-база)
- [Generated demo plots](#generated-demo-plots--автоматические-демо-графики)

---

## Why this repository matters / Почему этот репозиторий важен

This repository is not just a collection of markdown notes. It is structured as a **teaching and implementation path** from first SDR concepts to hardware-oriented project work.

Этот репозиторий — не просто набор markdown-файлов. Он оформлен как **учебный и инженерный маршрут** от первых понятий SDR до проектной работы, ориентированной на железо.

The course is designed around a complete engineering chain:

Курс построен вокруг полной инженерной цепочки:

**theory → modeling → fixed-point → HDL / FPGA → SDR board → external reception → IQ recording → analysis → circuit design → final project**

**теория → моделирование → fixed-point → HDL / FPGA → SDR-плата → внешний приём → запись IQ → анализ → схемотехника → итоговый проект**

---

## Generated demo plots / Автоматические демо-графики

Auto-generated IEEE-style plots are produced by GitHub Actions from `tools/generate_ieee_plots.py` and stored in `docs/assets`.

Графики в IEEE-style автоматически генерируются через GitHub Actions из `tools/generate_ieee_plots.py` и сохраняются в `docs/assets`.

| Lab | Demo plot | Engineering meaning |
|---|---|---|
| Lab 1 | Tone FFT | Peak frequency and noise floor |
| Lab 2 | AM vs FM spectrum | Modulation bandwidth comparison |
| Lab 3 | QPSK constellation | IQ quality and phase/noise effects |
| Lab 4 | Synchronization impact | CFO correction effect |
| Lab 5 | EVM vs impairments | Quantitative impairment comparison |
| Lab 6 | BER performance | End-to-end receiver quality |

### Lab 1 — Tone FFT
![Lab 1 FFT](docs/assets/lab01_fft.png)

### Lab 2 — AM vs FM Spectrum
![Lab 2 AM vs FM](docs/assets/lab02_am_vs_fm.png)

### Lab 3 — QPSK Constellation
![Lab 3 Constellation](docs/assets/lab03_constellation.png)

### Lab 4 — Synchronization Impact
![Lab 4 Synchronization](docs/assets/lab04_sync_constellation.png)

### Lab 5 — EVM vs Impairments
![Lab 5 EVM](docs/assets/lab05_evm.png)

### Lab 6 — BER Performance
![Lab 6 BER](docs/assets/lab06_ber.png)

---

## Current state / Текущее состояние

- **Block 1 is populated in bilingual form** / **Блок 1 наполнен в двуязычном формате**
- **IEEE-style plot generation is automated through GitHub Actions** / **Генерация IEEE-style графиков автоматизирована через GitHub Actions**
- **MkDocs deployment is temporarily manual** / **Деплой MkDocs временно переведён в ручной режим**
- **Visual landing pipeline is available** / **Добавлена наглядная карта инженерного маршрута**

---

## Hardware baseline / Аппаратная база

The current hands-on setup already includes a simple external receiver and a board-level SDR platform for practical experiments.

Текущая практическая аппаратная база уже включает простой внешний приёмник и SDR-платформу на уровне платы для лабораторных работ и экспериментов.

### RTL-SDR V3 Pro

![RTL-SDR V3 Pro](docs/images/hardware/rtl_sdr_v3_pro_real.png)

### Xilinx Zynq-7020 + ADR9363

![Xilinx Zynq-7020 with ADRV module](docs/images/hardware/xilinx_7020_adrv_real.png)

---

## SDR stand flow / Поток SDR-стенда

```mermaid
flowchart TB
    MODEL["1. Reference model<br/>MATLAB / Simulink expected waveform"]
    CFG["2. Experiment configuration<br/>frequency, gain, bandwidth and sample rate"]
    ZYNQ["3. Zynq-7020 + AD9363<br/>FPGA, ARM control and RF frontend"]
    PATH["4. RF path<br/>coax + attenuation or controlled over-the-air link"]
    RX["5. External receiver<br/>RTL-SDR as independent observation instrument"]
    RECORD["6. Observation and recording<br/>HDSDR spectrum, waterfall and IQ capture"]
    ANALYSIS["7. Offline analysis<br/>MATLAB, Python, C++ or GNU Radio replay"]

    MODEL --> CFG --> ZYNQ --> PATH --> RX --> RECORD --> ANALYSIS
    ANALYSIS -. model correction .-> MODEL
    ANALYSIS -. parameter tuning .-> CFG
```

**Practical flow:** generate a signal on the Zynq/ADRV platform → receive it with RTL-SDR → observe it in HDSDR → record IQ samples → analyze the recording in multiple software environments.

**Практический поток:** сформировать сигнал на платформе Zynq/ADRV → принять его через RTL-SDR → наблюдать в HDSDR → записать IQ-данные → проанализировать запись в нескольких программных средах.

## Level 2: Zynq / FPGA signal path / Уровень 2: тракт Zynq / FPGA

```mermaid
flowchart TB
    MODEL["Reference model<br/>expected samples and spectra"]
    CFG["Experiment configuration<br/>RF frequency, gain, bandwidth and data rate"]

    subgraph SOC["Zynq-7020 SoC"]
        direction TB
        PS["Processing System / ARM<br/>control software, scripts and register access"]
        PL["Programmable Logic / FPGA<br/>deterministic streaming DSP pipeline"]
        PS --> PL
    end

    AD["AD9363 RF frontend<br/>DAC, mixer, analog filters and I/Q interface"]
    LINK["RF link<br/>coax, attenuator or antenna path"]
    RX["External measurement chain<br/>RTL-SDR, HDSDR, IQ file and offline analysis"]

    MODEL --> PL
    CFG --> PS
    PL --> AD --> LINK --> RX
    RX -. model correction .-> MODEL
    RX -. parameter tuning .-> CFG
```

## Level 3: SDR TX/RX processing chain / Уровень 3: TX/RX тракт SDR

```mermaid
flowchart TB
    SRC["1. Source and framing<br/>tone, packet, payload or waveform definition"]
    MOD["2. Modulation and shaping<br/>BPSK/QPSK/QAM/FSK plus pulse-shaping filters"]
    TXRF["3. TX path<br/>DUC, DAC, mixer, filters and transmit gain"]
    CHANNEL["4. Channel<br/>coax, attenuator, antenna path, noise and offsets"]
    RXRF["5. RX path<br/>LNA, mixer, ADC, DDC and AGC"]
    SYNC["6. Synchronization and demodulation<br/>CFO, timing, frame sync, matched filter and bits"]
    VALID["7. Validation and replay<br/>IQ taps, FFT, EVM, BER, reports and notebooks"]

    SRC --> MOD --> TXRF --> CHANNEL --> RXRF --> SYNC --> VALID
    VALID -. model tuning .-> MOD
    VALID -. hardware tuning .-> RXRF
```

## Course blocks / Блоки курса

1. `blocks/block_01_intro_sdr`
2. `blocks/block_02_signals_and_sampling`
3. `blocks/block_03_dsp_basics`
4. `blocks/block_04_simulink_and_fixed_point`
5. `blocks/block_05_fpga_hdl_flow`
6. `blocks/block_06_rf_frontend_and_ad9363`
7. `blocks/block_07_tx_rx_chains`
8. `blocks/block_08_modulation_and_synchronization`
9. `blocks/block_09_recording_and_analysis_tools`

## License / Лицензия

MIT License
