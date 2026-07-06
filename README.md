# Zynq SDR Course

[![MkDocs](https://img.shields.io/badge/site-MkDocs%20Material-informational)](mkdocs.yml)
[![Full Course Smoke](https://github.com/Lay007/zynq-sdr-course/actions/workflows/full_course_smoke.yml/badge.svg)](https://github.com/Lay007/zynq-sdr-course/actions/workflows/full_course_smoke.yml)
[![Block 5 HDL](https://github.com/Lay007/zynq-sdr-course/actions/workflows/block5_hdl.yml/badge.svg)](https://github.com/Lay007/zynq-sdr-course/actions/workflows/block5_hdl.yml)
[![Block 8 Sync](https://github.com/Lay007/zynq-sdr-course/actions/workflows/block8_sync.yml/badge.svg)](https://github.com/Lay007/zynq-sdr-course/actions/workflows/block8_sync.yml)
[![Block 9 Recording](https://github.com/Lay007/zynq-sdr-course/actions/workflows/block9_recording_analysis.yml/badge.svg)](https://github.com/Lay007/zynq-sdr-course/actions/workflows/block9_recording_analysis.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Alexander%20Lyubko%20DSP-blue?logo=linkedin)](https://ru.linkedin.com/in/alexander-lyubko-dsp)

> A practical engineering course on Software-Defined Radio with DSP, fixed-point design, FPGA/HDL, Zynq, RF measurements and reproducible reporting.

**Russian version:** [README_RU.md](README_RU.md)

![Zynq SDR Course Pipeline](docs/assets/course_pipeline.svg)

---

## Overview

`zynq-sdr-course` is a bilingual SDR engineering course built around a complete model-to-measurement workflow:

```text
theory -> DSP model -> fixed-point design -> HDL/FPGA -> Zynq/AD9363 -> RF path -> IQ recording -> offline analysis -> engineering report
```

The repository is designed not only as a set of learning notes, but as a reproducible engineering workspace. It combines documentation, executable labs, HDL smoke checks, IQ metadata discipline, measurement templates and final-project structure.

---

## Who is this course for?

This course is useful for:

- students learning DSP, SDR and FPGA design;
- engineers moving from MATLAB/Python models to hardware-oriented implementation;
- FPGA developers who want a signal-processing project with real measurement context;
- instructors building a practical SDR/FPGA lab track;
- reviewers or recruiters evaluating DSP/FPGA engineering capability.

---

## What you will learn

| Layer | Engineering outcome |
|---|---|
| Signal theory | Sampling, bandwidth, aliasing, IQ representation and modulation basics |
| DSP modeling | FFT, FIR, windows, digital mixing, decimation and reference plots |
| Fixed-point design | Scaling, word length, saturation, quantization error and implementation risk |
| HDL / FPGA | Streaming DSP blocks, Verilog testbenches, latency and RTL/model comparison |
| Zynq + AD9363 | RF frontend configuration, gain planning and board-level experiment discipline |
| TX/RX chains | DUC/DDC, loopback metrics, packet detection and measurement flow |
| Synchronization | CFO, phase/timing recovery, EVM, BER and OFDM mini-link analysis |
| IQ data engineering | CI16/CU8/CF32 readers, metadata, dataset manifests and replay checks |
| Measurement reporting | SNR, EVM, BER, uncertainty notes, limitations and final engineering conclusions |

---

## Hardware baseline

The hardware-oriented part of the course is built around:

- **Xilinx Zynq-7020** class boards;
- **AD9363 / ADRV-compatible RF frontend modules**;
- **RTL-SDR** as an independent observation receiver;
- controlled RF paths with attenuation, metadata and safety notes.

The course can still be studied in simulation-only mode, because many labs have synthetic data, reproducible scripts and CI-backed checks.

---

## Repository structure

| Path | Purpose |
|---|---|
| `docs/` | MkDocs website pages, course maps, reports, guides and generated assets |
| `blocks/` | Course block source materials and lab implementations |
| `hardware/` | Curated local board bundles and bring-up starting points |
| `tools/` | Build, smoke-test and reproducibility scripts |
| `templates/` | Lab report, IQ metadata, RF safety and final-project templates |
| `datasets/` | Dataset manifests and lightweight dataset descriptors |
| `reports/` | FPGA reports, measurement examples and reviewer evidence maps |
| `experiments/` | Machine-checkable experiment manifests |

---

## Quick start

```bash
git clone https://github.com/Lay007/zynq-sdr-course.git
cd zynq-sdr-course
python tools/tasks.py install
python tools/tasks.py docs
python tools/tasks.py labs
```

Run the broader local smoke check:

```bash
python tools/tasks.py smoke
```

Run a CI-like local preflight before pushing larger changes:

```bash
python tools/run_local_ci.py
```

Useful commands:

| Command | Purpose |
|---|---|
| `python tools/tasks.py install` | Install Python dependencies |
| `python tools/tasks.py docs` | Build the MkDocs site in strict mode |
| `python tools/tasks.py serve` | Start a local documentation preview |
| `python tools/tasks.py labs` | Run representative executable Python labs |
| `python tools/tasks.py hdl` | Run Block 5 Verilog smoke tests |
| `python tools/tasks.py smoke` | Run docs + labs + HDL checks |
| `python tools/run_local_ci.py` | Run lint + pytest + docs + labs + canonical HDL smoke |
| `python tools/run_local_ci.py --quick` | Run lint + pytest + canonical HDL smoke |
| `python tools/check_dataset_manifests.py` | Validate dataset manifests and Git LFS pointer checksums |
| `python tools/tasks.py clean` | Remove generated local artifacts |

Curated local board starting point:

- [`hardware/7020_ad936x_sdr/README.md`](hardware/7020_ad936x_sdr/README.md) - imported Zynq-7020 + AD936x board bundle for bring-up work.

---

## Recommended learning path

1. **Intro to SDR** — tools, signals and first reception concepts.
2. **Signals and sampling** — spectrum, aliasing, complex baseband and IQ.
3. **DSP basics** — FFT, FIR, windows, mixing and decimation.
4. **Fixed-point workflow** — numeric formats, scaling and quantization.
5. **FPGA / HDL flow** — streaming interfaces, Verilog and testbenches.
6. **RF frontend** — frequency plans, gain staging and AD9363 settings.
7. **TX/RX chains** — DUC, DDC, loopback and packet-level metrics.
8. **Synchronization** — CFO, phase, timing, EVM and BER.
9. **IQ recording and analysis** — metadata, formats, replay and quality checks.
10. **Electronics and KiCad** — attenuators, filters and RF safety.
11. **Integrated SDR project** — model, implementation, capture and report.
12. **Final projects** — portfolio-ready SDR engineering outcomes.

---

## Key documentation pages

| Page | Why open it |
|---|---|
| [Course demo dashboard](docs/demo-dashboard.md) | Fast visual overview of executable course artifacts |
| [Visual course map](docs/course-map.md) | Complete route from theory to final project |
| [Student path](docs/student-path.md) | Shortest learner route through the repository |
| [Reviewer path](docs/reviewer-path.md) | Evidence-oriented review path for quick evaluation |
| [Reviewer acceptance checklist](docs/reviewer-checklist.md) | Pass/fail-style checklist for reproducibility, DSP, HDL, RF and final-project evidence |
| [Flagship reviewer report](reports/flagship_reviewer_report.md) | One-page portfolio-style evidence story with limitations and reproduction commands |
| [Course evidence map](reports/course-evidence-map.md) | Compact map of proven artifacts, gaps and next evidence actions |
| [Instructor guide](docs/instructor-guide.md) | How to use the repository as a teaching workspace |
| [Model → FPGA → RF → Measurement](docs/model-to-measurement.md) | Core engineering workflow of the course |
| [Course status](docs/status.md) | Readiness matrix, gaps and next improvements |
| [Reproducibility guide](docs/reproducibility-guide.md) | How to rebuild results and generated artifacts |
| [Real data policy](docs/real-data-policy.md) | How to handle IQ data without repository bloat |

---

## Engineering philosophy

The central idea of the course is:

```text
Model -> Implementation -> Measurement -> Decision
```

A result is considered mature only when it is connected to evidence: generated plots, metrics, HDL simulation, dataset metadata, RF safety notes or a reproducible engineering report.

---

## Current maturity focus

The repository already contains:

- bilingual MkDocs documentation;
- executable DSP and synchronization labs;
- HDL smoke checks for FPGA-facing examples;
- IQ recording and analysis workflows;
- real passive RTL-SDR air captures from the first SDR++ bring-up session, stored through Git LFS with manifests;
- dataset manifest consistency checking for Git LFS-backed captures;
- experiment manifests;
- report templates and final-project structure.

The next major proof points are:

- repeatable clean-boot BPSK/QPSK hardware qualification with success-rate reporting;
- a small publication-cleared measured QPSK IQ dataset beside the generated replay fixture;
- clean-boot correlation of the routed dual-modem bitstream with repeatable board results;
- complete QPSK or tone model-to-measurement final report.

---

## Portfolio value

This repository demonstrates practical competence in:

- DSP algorithm design;
- fixed-point implementation thinking;
- FPGA/HDL verification;
- SDR system architecture;
- RF measurement discipline;
- reproducible engineering documentation;
- CI-assisted educational workflow.

---

## License

MIT License. See [LICENSE](LICENSE).
