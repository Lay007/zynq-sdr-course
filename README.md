# Zynq SDR Course

[![MkDocs](https://img.shields.io/badge/site-MkDocs%20Material-informational)](mkdocs.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Alexander%20Lyubko%20DSP-blue?logo=linkedin)](https://ru.linkedin.com/in/alexander-lyubko-dsp)

> Engineering-oriented SDR course covering DSP, FPGA, RF and measurement workflows.

## Language

🇬🇧 **This README is intentionally English-first.**

🇷🇺 Full Russian documentation is available in:

**README_RU.md**

The Russian version contains the complete course description, explanations and study recommendations.

---

## What is this repository?

Zynq SDR Course is a practical learning path that connects:

```text
Signal Theory
    ↓
DSP Algorithms
    ↓
MATLAB / Simulink Models
    ↓
Fixed-Point Design
    ↓
Verilog / FPGA
    ↓
Zynq + AD9363 Hardware
    ↓
RF Measurements
    ↓
Engineering Reports
```

Unlike many SDR tutorials, the goal is not only to simulate signals but to build a complete engineering workflow from theory to hardware validation.

---

## Main Topics

- SDR fundamentals
- Signals and sampling
- FFT, FIR and DSP basics
- MATLAB and Simulink workflow
- Fixed-point implementation
- FPGA and Verilog design
- Zynq-7000 architecture
- AD9363 RF transceiver
- TX/RX chains
- Synchronization and carrier recovery
- IQ recording and analysis
- RF measurements
- KiCad and basic electronics
- Final SDR projects

---

## Target Hardware

- Xilinx Zynq-7020
- AD9363 / ADRV-based SDR modules
- RTL-SDR for independent measurements

---

## Quick Start

```bash
git clone https://github.com/Lay007/zynq-sdr-course.git
cd zynq-sdr-course
python tools/tasks.py install
python tools/tasks.py docs
python tools/tasks.py labs
```

Full validation:

```bash
python tools/tasks.py smoke
```

---

## Recommended Reading Order

1. Intro to SDR
2. Signals and Sampling
3. DSP Basics
4. Simulink and Fixed-Point
5. FPGA HDL Flow
6. RF Frontend and AD9363
7. TX/RX Chains
8. Modulation and Synchronization
9. Recording and Analysis
10. KiCad and Electronics
11. Integrated SDR Project
12. Final Project

---

## Key Pages

- `docs/course-map.md`
- `docs/student-path.md`
- `docs/reviewer-path.md`
- `docs/model-to-measurement.md`
- `docs/status.md`
- `docs/reproducibility-guide.md`

---

## Engineering Philosophy

The course follows the workflow:

```text
Model → Fixed Point → FPGA → RF → Measurement → Report
```

Every major topic is expected to produce measurable and reproducible engineering artifacts.

---

## License

MIT License