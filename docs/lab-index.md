# Lab Index

This page provides a compact index of course labs. It is intentionally shorter than the MkDocs navigation tree and is used as a planning checklist.

## Legend

| Mark | Meaning |
|---|---|
| `yes` | A page, script, report task or reusable evidence path exists. |
| `partial` | Present, but still needs stronger examples or final packaging. |
| `manual` | Requires instructor or local bench execution. |
| `ci` | Covered by GitHub Actions or the representative smoke path. |

## Compact lab coverage

| Block | Labs | Main coverage | State | Next improvement |
|---|---|---|---|---|
| 01 | 1.0-1.1 | first observation and learner report flow | manual / measured | add a compact comparison report |
| 02 | 2.1-2.3 | sampling axis, aliasing and I/Q interpretation | ci / executable | add C++ bridge and metadata-error examples |
| 03 | 3.1-3.7 | FFT, FIR, mixing, decimation, convolution and windows | partial ci / executable | add more canonical outputs |
| 04 | 4.1-4.4 | fixed-point workflow and model handoff | partial ci / executable | tighten implementation handoff constraints |
| 05 | 5.1-5.11 | streaming interfaces, RTL mapping, self-checking tests and routed evidence | ci / executable | correlate implementation with board runs |
| 06 | 6.1-6.8 plus 6.9 extension | frontend setup, artifact interpretation and measurement preparation | partial ci + manual | add a reviewed measurement package |
| 07 | 7.1-7.5 | chain architecture and link-level metrics | partial ci / executable | add measured examples |
| 08 | 8.1-8.10, 8.20-8.21 | synchronization, QPSK, OFDM mini-link, OFDM PAPR/clipping, coding, SNR/BER traps and executable CSS waveform/detector | ci / executable | add packet-level CSS/LoRa-like synchronization and FPGA mapping |
| 09 | 9.1-9.5 | metadata, file readers and replay analysis | ci / executable | keep manifests and thresholds synchronized |
| 10 | 10.1-10.6 | electronics, RF safety, attenuators, NanoVNA/S-parameters and schematic mini-project | manual / measured | add real NanoVNA CSV/Touchstone exports and final edited photos |
| 11 | 11.1-11.28 | integrated project workflow and bring-up evidence | manual + measured | add controlled-cabled/long-duration statistics and seed/rebuild timing robustness |
| 12 | 12.1-12.4 | final project briefs, rubric, templates and filled implementation report | reviewable / hardware pending | complete the open measurement gates |

## Numbering note

The MkDocs-visible Lab 6.7 is **Zero-IF artifacts**. The separate power-scale material is tracked here as a Block 6 extension, so the lab index no longer conflicts with the navigation tree.

Block 8 uses `8.10-8.19` for OFDM/QAM implementation labs. The CSS track starts at `8.20` so that waveform families remain easy to identify without renumbering the existing synchronization and hardware evidence pages.

## Recommended assessment path

1. Run `python tools/tasks.py labs`.
2. Run `python tools/tasks.py hdl` if Icarus Verilog is installed.
3. Review generated artifacts in `docs/assets`.
4. Fill the lab report template from `templates/lab_report.template.md`.
5. Use Block 11 to combine selected results into a final project.
