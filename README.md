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

### RTL-SDR V3 Pro

![RTL-SDR V3 Pro](docs/images/hardware/rtl_sdr_v3_pro_real.png)

### Xilinx Zynq-7020 + ADR9363

![Xilinx Zynq-7020 with ADRV module](docs/images/hardware/xilinx_7020_adrv_real.png)

### SDR stand flow / Поток SDR-стенда

```mermaid
flowchart TB
    %% ===== LIGHT STYLE =====
    classDef model fill:#E0F2FE,color:#0F172A,stroke:#0284C7,stroke-width:1px;
    classDef fpga fill:#DCFCE7,color:#0F172A,stroke:#16A34A,stroke-width:1px;
    classDef arm fill:#FEF9C3,color:#0F172A,stroke:#CA8A04,stroke-width:1px;
    classDef rf fill:#FFE4E6,color:#0F172A,stroke:#E11D48,stroke-width:1px;
    classDef data fill:#EDE9FE,color:#0F172A,stroke:#7C3AED,stroke-width:1px;

    M["MATLAB / Simulink<br/>Reference model"]:::model
    CFG["Configuration<br/>frequency / gain / sample rate"]:::arm
    ZYNQ["Zynq-7020 + AD9363<br/>FPGA / ARM / RF frontend"]:::fpga
    AIR["RF path<br/>over the air / coax cable"]:::rf
    RTL["RTL-SDR<br/>external receiver"]:::data
    HDSDR["HDSDR<br/>spectrum / waterfall / recording"]:::data
    IQ["IQ recording<br/>WAV / RAW / CI16"]:::data
    ANALYSIS["Offline analysis<br/>MATLAB / Python / C++ / GNU Radio"]:::model

    M --> CFG --> ZYNQ --> AIR --> RTL --> HDSDR --> IQ --> ANALYSIS
    ANALYSIS -. model correction .-> M
    ANALYSIS -. parameter tuning .-> CFG
```

**Practical flow:** generate a signal on the Zynq/ADRV platform → receive it with RTL-SDR → observe it in HDSDR → record IQ samples → analyze the recording in multiple software environments.

**Практический поток:** сформировать сигнал на платформе Zynq/ADRV → принять его через RTL-SDR → наблюдать в HDSDR → записать IQ-данные → проанализировать запись в нескольких программных средах.

### Level 2: Zynq / FPGA signal path / Уровень 2: тракт Zynq / FPGA

```mermaid
flowchart TB
    %% ===== LIGHT STYLE =====
    classDef model fill:#E0F2FE,color:#0F172A,stroke:#0284C7,stroke-width:1px;
    classDef fpga fill:#DCFCE7,color:#0F172A,stroke:#16A34A,stroke-width:1px;
    classDef arm fill:#FEF9C3,color:#0F172A,stroke:#CA8A04,stroke-width:1px;
    classDef rf fill:#FFE4E6,color:#0F172A,stroke:#E11D48,stroke-width:1px;
    classDef data fill:#EDE9FE,color:#0F172A,stroke:#7C3AED,stroke-width:1px;

    M["MATLAB / Simulink<br/>reference model"]:::model
    CFG["Experiment configuration<br/>frequency / gain / sample rate"]:::arm

    subgraph Z["Zynq-7020 SoC"]
        direction TB

        subgraph PS["Processing System / ARM"]
            direction TB
            SW["Control software<br/>Linux / bare-metal / scripts"]:::arm
            IIO["IIO / SPI control<br/>AD9363 registers"]:::arm
            SW --> IIO
        end

        subgraph PL["Programmable Logic / FPGA"]
            direction TB
            DDS["DDS / NCO<br/>tone generation"]:::fpga
            MIX["Digital mixer<br/>frequency shift"]:::fpga
            FIR["FIR filter<br/>pulse shaping / LPF"]:::fpga
            INT["Interpolator<br/>sample-rate adaptation"]:::fpga
            AXI["AXI-Stream interface"]:::fpga
            DDS --> MIX --> FIR --> INT --> AXI
        end
    end

    AD["AD9363 RF frontend<br/>DAC / mixer / analog filters"]:::rf
    AIR["RF signal<br/>over the air / coax cable"]:::rf
    RTL["RTL-SDR receiver"]:::data
    HDSDR["HDSDR<br/>spectrum / waterfall / recording"]:::data
    IQ["IQ file<br/>WAV / RAW / CI16"]:::data
    ANALYSIS["Offline analysis<br/>MATLAB / Python / GNU Radio"]:::model

    M --> DDS
    CFG --> SW
    IIO --> AD
    AXI --> AD
    AD --> AIR --> RTL --> HDSDR --> IQ --> ANALYSIS

    ANALYSIS -. model correction .-> M
    ANALYSIS -. parameter tuning .-> CFG
```

This second-level diagram explains what happens inside the board-level part of the stand: the ARM side configures the experiment and RF frontend, while the FPGA side implements the deterministic sample-processing chain.

Эта диаграмма второго уровня показывает, что происходит внутри платной части стенда: ARM-часть настраивает эксперимент и радиотракт, а FPGA-часть реализует детерминированную цепочку обработки отсчётов.

### Level 3: SDR TX/RX processing chain / Уровень 3: TX/RX тракт SDR

```mermaid
flowchart TB
    %% ===== LIGHT STYLE =====
    classDef src fill:#E0F2FE,color:#0F172A,stroke:#0284C7,stroke-width:1px;
    classDef dsp fill:#DCFCE7,color:#0F172A,stroke:#16A34A,stroke-width:1px;
    classDef sync fill:#FEF3C7,color:#0F172A,stroke:#D97706,stroke-width:1px;
    classDef rf fill:#FFE4E6,color:#0F172A,stroke:#E11D48,stroke-width:1px;
    classDef io fill:#EDE9FE,color:#0F172A,stroke:#7C3AED,stroke-width:1px;
    classDef metric fill:#F1F5F9,color:#0F172A,stroke:#64748B,stroke-width:1px;

    subgraph TX["TX chain / Передающий тракт"]
        direction TB
        SRC["Signal source<br/>tone / packet / waveform"]:::src
        MOD["Modulator<br/>BPSK / QPSK / QAM / FSK"]:::dsp
        RRC_TX["Pulse shaping<br/>RRC / FIR"]:::dsp
        DUC["DUC<br/>interpolation + digital upconversion"]:::dsp
        DAC["DAC path<br/>AD9363 TX"]:::rf
        RF_TX["RF transmit chain<br/>mixer / PA / filters"]:::rf
        SRC --> MOD --> RRC_TX --> DUC --> DAC --> RF_TX
    end

    CH["Channel<br/>coax / attenuator / over-the-air"]:::rf

    subgraph RX["RX chain / Приёмный тракт"]
        direction TB
        RF_RX["RF receive chain<br/>LNA / mixer / filters"]:::rf
        ADC["ADC path<br/>AD9363 RX or RTL-SDR"]:::rf
        DDC["DDC<br/>digital downconversion + decimation"]:::dsp
        AGC["AGC<br/>level control"]:::sync
        SYNC["Synchronization<br/>CFO / timing / frame"]:::sync
        RRC_RX["Matched filter<br/>RRC / FIR"]:::dsp
        DEMOD["Demodulator<br/>symbols / bits"]:::dsp
        RF_RX --> ADC --> DDC --> AGC --> SYNC --> RRC_RX --> DEMOD
    end

    subgraph VALIDATION["Validation and replay / Проверка и повторный анализ"]
        direction TB
        IQ["IQ capture points<br/>raw / WAV / CI16"]:::io
        METRICS["Validation metrics<br/>FFT / EVM / BER / SNR"]:::metric
        REPORT["Reports<br/>plots / notebooks / lab results"]:::io
        IQ --> METRICS --> REPORT
    end

    RF_TX --> CH --> RF_RX
    DEMOD --> METRICS

    DUC -. TX IQ tap .-> IQ
    ADC -. RX raw IQ tap .-> IQ
    DDC -. baseband IQ tap .-> IQ
    IQ -. offline replay .-> DDC
    METRICS -. model tuning .-> MOD
    METRICS -. hardware tuning .-> AGC
```

Level 3 turns the stand into a complete SDR engineering pipeline: signal generation, modulation, pulse shaping, digital up/down conversion, RF transfer, synchronization, demodulation, and objective validation through FFT/EVM/BER/SNR metrics.

Уровень 3 превращает стенд в полный инженерный SDR-конвейер: генерация сигнала, модуляция, формирующая фильтрация, цифровое повышение/понижение частоты, RF-передача, синхронизация, демодуляция и объективная проверка через FFT/EVM/BER/SNR.

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
10. `blocks/block_01_intro_sdr0`
11. `blocks/block_01_intro_sdr1`
12. `blocks/block_01_intro_sdr2`

## License / Лицензия

MIT License
