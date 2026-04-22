# Bilingual SDR Course: From Theory to Board-Level Implementation

## Purpose
This archive contains a **full course scaffold** in a parallel bilingual format:
- Russian content in separate `*_ru.md` files;
- English content in separate `*_en.md` files.

The course is designed as an engineering route from signal theory to practical implementation on an SDR board, including recording analysis, circuit design, KiCad, Simulink, FPGA flow, and a final project.

## What is included
- root `README.md` with navigation;
- `README_ru.md` and `README_en.md`;
- `COURSE_STRUCTURE_ru.md` and `COURSE_STRUCTURE_en.md`;
- `LAB_TRACK_ru.md` and `LAB_TRACK_en.md`;
- `MEDIA_GUIDE_ru.md` and `MEDIA_GUIDE_en.md`;
- `blocks/` directory containing all course modules;
- a **fully populated Block 1**;
- structured placeholders for later blocks with goals, contents, and folder recommendations.

## Course format
Recommended format:
- theory;
- demonstration;
- lab work;
- recording and analysis;
- transition to model or hardware implementation;
- report.

## Main learning chain
**theory → model → fixed-point → HDL/FPGA → SDR board → external reception → IQ recording → analysis → circuit design → final project**

## Navigation
- [Course structure](COURSE_STRUCTURE_en.md)
- [Lab track](LAB_TRACK_en.md)
- [Guide for photos, schematics, and animation](MEDIA_GUIDE_en.md)

## Course blocks
1. `block_01_intro_sdr` — introduction, tools, and first signal reception  
2. `block_02_signals_and_sampling` — signals, spectrum, sampling, IQ  
3. `block_03_dsp_basics` — FFT, filtering, windows, basic DSP operations  
4. `block_04_simulink_and_fixed_point` — modeling, fixed-point, hardware preparation  
5. `block_05_fpga_hdl_flow` — Simulink/HDL/Vivado/SoC route  
6. `block_06_rf_frontend_and_ad9363` — RF chain, levels, frequencies, AD9363  
7. `block_07_tx_rx_chains` — transmit and receive chains, DUC/DDC  
8. `block_08_modulation_and_synchronization` — modulation, demodulation, synchronization  
9. `block_09_recording_and_analysis_tools` — HDSDR, GNU Radio, MATLAB, Python, C++  
10. `block_10_kicad_and_basic_electronics` — KiCad, breadboard, analog and digital support circuits  
11. `block_11_integrated_sdr_project` — integrated educational SDR project  
12. `block_12_final_projects` — final project work


## Course website

After GitHub Pages is enabled, the materials will also be available as a website:

- `https://lay007.github.io/zynq-sdr-course/`

The site is built with **MkDocs Material** and deployed through **GitHub Actions**.

## Current state
Block 1 is already suitable for publishing in a repository and continuing development. The remaining blocks are provided as strong bilingual scaffolds so they can be filled in one by one in the same style.
