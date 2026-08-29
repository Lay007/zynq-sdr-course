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
| 05 | 5.1-5.12 | streaming interfaces, RTL mapping, self-checking tests, AXI-Lite control and the Zynq PS/PL mailbox boundary | ci / executable + board step pending | complete the physical PS→PL→PS mailbox echo on Zynq |
| 06 | 6.1-6.9 | frontend setup, calibration, zero-IF artifacts and RTL-SDR/AD936x receiver comparison | executable + manual bench | record a reviewed two-receiver measurement package |
| 07 | 7.1-7.5 | chain architecture and link-level metrics | partial ci / executable | add measured examples |
| 08 | 8.1-8.10, 8.20-8.21 | synchronization, QPSK, OFDM mini-link, OFDM PAPR/clipping, coding, SNR/BER traps and executable CSS waveform/detector | ci / executable | keep advanced waveform work secondary to the core educational path; real LoRa PHY continues in zynq-lora-phy-positioning |
| 09 | 9.1-9.5 | metadata, file readers and replay analysis | ci / executable | keep manifests and thresholds synchronized |
| 10 | 10.1-10.6 | electronics, RF safety, attenuators, NanoVNA/S-parameters and schematic mini-project | manual / measured | add real NanoVNA CSV/Touchstone exports and final edited photos |
| 11 | 11.1-11.46 | integrated project workflow, bring-up, BER/CFO/timing evidence, two-board QPSK and the user-visible PS→PL→RF→PL→PS message goal | measured / message integration pending | pass a text message between two boards and print it in the receiving console |
| 12 | 12.1-12.4 | final project briefs, rubric, templates and filled implementation report | reviewable / hardware pending | complete the open measurement gates |

## Block 5 PS/PL bridge

Lab 5.12 adds the missing system-level bridge between HDL exercises and RF bring-up:

- [Zynq PS/PL architecture](zynq-ps-pl-architecture.md)
- [English Lab 5.12](en/labs/lab-5-12-zynq-ps-pl-mailbox.md)
- [Russian Lab 5.12](ru/labs/lab-5-12-zynq-ps-pl-mailbox.md)

The first executable step is board-independent:

```bash
python tools/zynq_message_console.py --mock demo "Hello Zynq" --sequence 17
```

The first hardware step is deliberately not DMA. It is a small AXI-Lite mailbox and a PL echo so the learner can directly observe the PS→AXI→PL→AXI→PS transaction before the same software-facing contract is connected to the QPSK radio path.

## Block 6 receiver-comparison extension

Lab 6.9 adds a reproducible offline analyzer and a conducted-bench procedure:

- [English lab description](https://github.com/Lay007/zynq-sdr-course/blob/main/blocks/block_06_rf_frontend_and_ad9363/lab_6_9_receiver_comparison.md)
- [Russian lab description](https://github.com/Lay007/zynq-sdr-course/blob/main/blocks/block_06_rf_frontend_and_ad9363/lab_6_9_receiver_comparison_ru.md)
- [Python analyzer](https://github.com/Lay007/zynq-sdr-course/blob/main/blocks/block_06_rf_frontend_and_ad9363/python/lab_6_9_compare_receivers.py)

The executable synthetic mode is suitable for unit tests. The final engineering
result still requires matched real IQ captures from RTL-SDR and the Pluto-compatible
AD936x receiver, fixed manual gains, measured passive losses and a common analysis
bandwidth.

## Numbering note

The MkDocs-visible Lab 6.7 is **Zero-IF artifacts**. The separate power-scale material is tracked as a Block 6 extension and Lab 6.9 is the receiver-comparison experiment, so the navigation numbering remains unambiguous.

Block 8 uses `8.10-8.19` for OFDM/QAM implementation labs. The CSS track starts at `8.20` so that waveform families remain easy to identify without renumbering the existing synchronization and hardware evidence pages.

## Recommended assessment path

1. Run `python tools/tasks.py labs`.
2. Run `python tools/tasks.py hdl` if Icarus Verilog is installed.
3. Run `python tools/zynq_message_console.py --mock demo "Hello Zynq" --sequence 17` and explain the PS/PL register contract.
4. Run the Lab 6.9 synthetic baseline or analyze matched real IQ captures.
5. Review generated artifacts in `docs/assets`.
6. Fill the lab report template from `templates/lab_report.template.md`.
7. Use Block 11 to combine selected results into a final project, preferably ending with a visible two-board message exchange.
