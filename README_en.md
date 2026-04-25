# Zynq SDR Course: From Theory to Board-Level Implementation

[![Bilingual](https://img.shields.io/badge/language-RU%20%2F%20EN-blueviolet)](#)
[![MkDocs](https://img.shields.io/badge/site-MkDocs%20Material-informational)](#)
[![Pages](https://github.com/Lay007/zynq-sdr-course/actions/workflows/pages.yml/badge.svg)](https://github.com/Lay007/zynq-sdr-course/actions/workflows/pages.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A **bilingual engineering course on SDR** designed as a structured path from signal theory to practical implementation on a Zynq-based SDR platform.

The course is intentionally built not as a loose set of notes, but as a coherent learning route that connects:

- signal theory;
- SDR fundamentals;
- DSP foundations;
- Simulink modeling and fixed-point preparation;
- HDL / FPGA flow;
- RF front-end understanding;
- recording and analysis tools;
- basic electronics and KiCad;
- integrated final projects.

## Purpose

The repository is designed for learners and practitioners who want to move beyond isolated SDR experiments and follow a more complete engineering chain:

**theory → model → fixed-point → HDL / FPGA → SDR board → external reception → IQ recording → analysis → circuit design → final project**

## What is included

- root `README.md` as a bilingual landing page;
- `README_ru.md` and `README_en.md` for language-specific navigation;
- `COURSE_STRUCTURE_ru.md` and `COURSE_STRUCTURE_en.md`;
- `LAB_TRACK_ru.md` and `LAB_TRACK_en.md`;
- `MEDIA_GUIDE_ru.md` and `MEDIA_GUIDE_en.md`;
- the `blocks/` directory containing all course modules;
- a **fully populated Block 1**;
- structured bilingual scaffolds for the remaining blocks.

## Course website

The repository already includes a documentation site configuration based on **MkDocs Material** and a **GitHub Pages deployment workflow**.

Configured site URL:

- `https://lay007.github.io/zynq-sdr-course/`

## Hardware baseline

The current hands-on setup already includes a simple external receiver and a board-level SDR platform for practical experiments.

### RTL-SDR V3 Pro

![RTL-SDR V3 Pro](docs/images/hardware/rtl_sdr_v3_pro.svg)

The RTL-SDR dongle is used as an accessible external receiver for the first reception, capture, and observation tasks.

### Xilinx Zynq-7020 + ADRV module

![Xilinx Zynq-7020 with ADRV module](docs/images/hardware/xilinx_7020_adrv_angle_1.svg)

This photo shows the actual board-level SDR platform used for the practical hardware-oriented part of the course.

### SDR stand diagram

![SDR training stand diagram](docs/images/hardware/sdr_stand_diagram.svg)

## Navigation

- [Bilingual landing page](README.md)
- [Course structure](COURSE_STRUCTURE_en.md)
- [Lab track](LAB_TRACK_en.md)
- [Guide for photos, schematics, and animation](MEDIA_GUIDE_en.md)
- [Russian version](README_ru.md)

## Course blocks

1. `block_01_intro_sdr` — introduction, tools, and first signal reception
2. `block_02_signals_and_sampling` — signals, spectrum, sampling, IQ
3. `block_03_dsp_basics` — FFT, filtering, windows, and basic DSP operations
4. `block_04_simulink_and_fixed_point` — modeling, fixed-point, and preparation for hardware
5. `block_05_fpga_hdl_flow` — Simulink, HDL, Vivado, and SoC flow
6. `block_06_rf_frontend_and_ad9363` — RF chain, levels, frequencies, and AD9363
7. `block_07_tx_rx_chains` — transmit and receive chains, DUC, and DDC
8. `block_08_modulation_and_synchronization` — modulation, demodulation, and synchronization
9. `block_09_recording_and_analysis_tools` — HDSDR, GNU Radio, MATLAB, Python, and C++
10. `block_10_kicad_and_basic_electronics` — KiCad, breadboard work, and support circuits
11. `block_11_integrated_sdr_project` — integrated educational SDR project
12. `block_12_final_projects` — final project work

## Current state

- **Block 1 is already fully populated in bilingual form**
- **The remaining blocks are prepared as strong bilingual scaffolds**
- **The repository is ready for iterative expansion and publication as a course website**

## Why this repository is strong

- it presents the course in a parallel bilingual format instead of mixing languages in one file;
- it explicitly bridges theory and implementation;
- it combines DSP, modeling, FPGA flow, RF understanding, recording analysis, and basic electronics;
- it is readable both as a GitHub repository and as a documentation website.

## Recommended next steps

- continue filling Blocks 2–12 in the same style;
- add more diagrams, board photos, and schematics to hardware-focused sections;
- enrich labs with IQ recordings, datasets, and analysis scripts;
- expand the end-to-end practical project path.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
