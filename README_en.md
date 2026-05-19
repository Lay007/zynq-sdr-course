# Zynq SDR Course: From Theory to Board-Level Implementation

[![Bilingual](https://img.shields.io/badge/language-RU%20%2F%20EN-blueviolet)](#)
[![MkDocs](https://img.shields.io/badge/site-MkDocs%20Material-informational)](mkdocs.yml)
[![Pages](https://github.com/Lay007/zynq-sdr-course/actions/workflows/pages.yml/badge.svg)](https://github.com/Lay007/zynq-sdr-course/actions/workflows/pages.yml)
[![Full Course Smoke](https://github.com/Lay007/zynq-sdr-course/actions/workflows/full_course_smoke.yml/badge.svg)](https://github.com/Lay007/zynq-sdr-course/actions/workflows/full_course_smoke.yml)
[![Block 5 HDL](https://github.com/Lay007/zynq-sdr-course/actions/workflows/block5_hdl.yml/badge.svg)](https://github.com/Lay007/zynq-sdr-course/actions/workflows/block5_hdl.yml)
[![Block 8 Sync](https://github.com/Lay007/zynq-sdr-course/actions/workflows/block8_sync.yml/badge.svg)](https://github.com/Lay007/zynq-sdr-course/actions/workflows/block8_sync.yml)
[![Block 9 Recording](https://github.com/Lay007/zynq-sdr-course/actions/workflows/block9_recording_analysis.yml/badge.svg)](https://github.com/Lay007/zynq-sdr-course/actions/workflows/block9_recording_analysis.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A **bilingual engineering course on Software-Defined Radio** that connects theory, modeling, fixed-point DSP, HDL/FPGA implementation, RF hardware, IQ recording, measurement and final project reporting.

This repository is designed as an end-to-end route rather than a loose collection of notes:

```text
theory -> modeling -> fixed-point -> HDL/FPGA -> Zynq/AD9363 -> RF path -> external receiver -> IQ recording -> analysis -> electronics -> final project
```

## Course website

- Published documentation: <https://lay007.github.io/zynq-sdr-course/>
- Bilingual landing page: [README.md](README.md)
- Russian version: [README_ru.md](README_ru.md)

## Start locally in 10 minutes

```bash
git clone https://github.com/Lay007/zynq-sdr-course.git
cd zynq-sdr-course
python tools/tasks.py install
python tools/tasks.py docs
python tools/tasks.py labs
```

For the full local smoke check, install Icarus Verilog (`iverilog`) and run:

```bash
python tools/tasks.py smoke
```

| Command | Purpose |
|---|---|
| `python tools/tasks.py install` | Install Python dependencies |
| `python tools/tasks.py docs` | Build the MkDocs site in strict mode |
| `python tools/tasks.py serve` | Preview the MkDocs site locally |
| `python tools/tasks.py labs` | Run representative executable Python labs |
| `python tools/tasks.py hdl` | Run Block 5 Verilog smoke tests |
| `python tools/tasks.py smoke` | Run docs + labs + HDL checks |
| `python tools/tasks.py clean` | Remove generated local artifacts |

## Fast navigation

| Page | Why open it |
|---|---|
| [Course demo dashboard](docs/demo-dashboard.md) | Fast visual overview of generated course artifacts |
| [Visual course map](docs/course-map.md) | Complete route from theory to final project |
| [Model → FPGA → RF → Measurement](docs/model-to-measurement.md) | Core system-level bridge used throughout the course |
| [Hardware experiment roadmap](docs/hardware-experiment-roadmap.md) | Practical path from board bring-up to RF observations |
| [Lab index](docs/lab-index.md) | Executable and documentation-based labs in one place |
| [Reproducibility guide](docs/reproducibility-guide.md) | How to rebuild results and generated assets |
| [Real data policy](docs/real-data-policy.md) | How to store, describe and reference IQ captures |
| [Portfolio view](docs/portfolio-view.md) | What the repository demonstrates as an engineering portfolio item |

## What the course teaches

| Layer | Engineering outcome |
|---|---|
| Signals and spectra | Sampling, bandwidth, aliasing, complex baseband and modulation basics |
| DSP modeling | FFT, FIR, windows, digital mixing, decimation and reference plots |
| Fixed-point DSP | Word length, scaling, quantization error and implementation trade-offs |
| HDL / FPGA | Streaming DSP blocks, Verilog testbenches, latency and RTL comparison |
| Zynq + AD9363 hardware | RF configuration, gain/frequency planning and board-level experiments |
| TX/RX chains | DUC/DDC, loopback metrics, packet detection and measurement flow |
| Synchronization | CFO, phase/timing recovery, EVM, BER and OFDM mini-link analysis |
| IQ recording | CI16/CU8/CF32 readers, metadata, capture quality checks and replay |
| Electronics / KiCad | Attenuators, RC filters, RF safety and schematic discipline |
| Final project | Requirements, architecture, measurement report and portfolio-ready result |

## Repository structure

| Path | Role |
|---|---|
| `docs/` | MkDocs website content, bilingual pages, generated assets and figures |
| `blocks/` | Source course blocks and lab materials |
| `tools/` | Reproducibility, build and lab automation scripts |
| `templates/` | Lab report, capture metadata, RF safety and final report templates |
| `COURSE_STRUCTURE_en.md` | English high-level course structure |
| `LAB_TRACK_en.md` | English laboratory trajectory |
| `MEDIA_GUIDE_en.md` | Guide for photos, schematics, animations and generated visuals |

## Hardware baseline

The practical setup combines an accessible independent receiver with a board-level SDR platform. This makes the first RF experiments observable before the learner dives deeply into FPGA and RF internals.

### RTL-SDR V3 Pro

![RTL-SDR V3 Pro](docs/images/hardware/rtl_sdr_v3_pro_real.png)

The RTL-SDR dongle is used as an external observation receiver for first reception, spectrum viewing, waterfall analysis and IQ capture tasks.

### Xilinx Zynq-7020 + AD9363/ADRV module

![Xilinx Zynq-7020 with ADRV module](docs/images/hardware/xilinx_7020_adrv_real.png)

The Zynq-based SDR board is the target platform for the hardware-oriented part of the course: model-driven signal generation, FPGA/SoC integration, RF configuration and measurement.

### SDR training stand

![SDR training stand diagram](docs/images/hardware/sdr_stand_diagram.svg)

Practical flow: **model a signal → configure the Zynq/AD9363 platform → transmit or route the signal through a controlled RF path → receive it with RTL-SDR → observe it in HDSDR → record IQ → analyze the recording in MATLAB, Python, C++ or GNU Radio**.

## Course blocks

1. [`blocks/block_01_intro_sdr`](blocks/block_01_intro_sdr) — introduction, tools and first signal reception
2. [`blocks/block_02_signals_and_sampling`](blocks/block_02_signals_and_sampling) — signals, spectrum, sampling and IQ
3. [`blocks/block_03_dsp_basics`](blocks/block_03_dsp_basics) — FFT, filtering, windows and DSP operations
4. [`blocks/block_04_simulink_and_fixed_point`](blocks/block_04_simulink_and_fixed_point) — modeling, fixed-point and hardware preparation
5. [`blocks/block_05_fpga_hdl_flow`](blocks/block_05_fpga_hdl_flow) — Simulink, HDL, Vivado, SoC and testbenches
6. [`blocks/block_06_rf_frontend_and_ad9363`](blocks/block_06_rf_frontend_and_ad9363) — RF chain, levels, frequency planning and AD9363
7. [`blocks/block_07_tx_rx_chains`](blocks/block_07_tx_rx_chains) — TX/RX chains, DUC, DDC and loopback metrics
8. [`blocks/block_08_modulation_and_synchronization`](blocks/block_08_modulation_and_synchronization) — modulation, demodulation, synchronization, BER and EVM
9. [`blocks/block_09_recording_and_analysis_tools`](blocks/block_09_recording_and_analysis_tools) — HDSDR, GNU Radio, MATLAB, Python and C++ analysis
10. [`blocks/block_10_kicad_and_basic_electronics`](blocks/block_10_kicad_and_basic_electronics) — KiCad, breadboard work, attenuators, filters and RF safety
11. [`blocks/block_11_integrated_sdr_project`](blocks/block_11_integrated_sdr_project) — integrated educational SDR project
12. [`blocks/block_12_final_projects`](blocks/block_12_final_projects) — final project work and engineering report

## Current engineering status

- The course has a bilingual MkDocs structure with Russian and English navigation.
- Block 1 is fully populated and the later blocks are prepared as structured learning modules.
- Blocks 3–11 already include executable or measurement-oriented lab pages in the documentation site.
- CI workflows cover MkDocs publication, full-course smoke checks, HDL tests, synchronization labs and recording/analysis checks.
- Generated IEEE-style plots and reproducibility summaries are stored under `docs/assets`.

## Why this repository is strong

- It demonstrates a complete engineering chain, not only SDR theory.
- It bridges MATLAB/Simulink-style modeling with fixed-point, HDL, RF and measurement.
- It uses real hardware context: Zynq-7020, AD9363/ADRV, RTL-SDR and HDSDR.
- It is useful both as a teaching course and as a portfolio-grade engineering repository.
- It is built for reproducibility: scripts, templates, CI workflows and generated figures are part of the project.

## Recommended next improvements

1. Add a single top-level `docs/status.md` page that summarizes completion percentage, lab readiness and hardware dependencies per block.
2. Add small validated IQ demo files through Git LFS or external dataset manifests instead of storing large captures directly in the repository.
3. Add a hardware safety page with attenuation limits, RF power assumptions and safe connection diagrams.
4. Add a contributor guide for adding new labs in both languages with required Python/MATLAB/C++/Verilog artifacts.
5. Add one final end-to-end demo: generated tone on the board, RTL-SDR capture, IQ metadata, replay script and final measurement report.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
