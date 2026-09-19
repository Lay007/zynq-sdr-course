# Block 11. Integrated SDR Project

## Purpose
This block combines the previously studied elements into one system: model, DSP chain, hardware platform, analysis tools, and documentation.

## Why this block matters
Here the student learns system-level integration rather than isolated operations, with all subsystems required to work together.

## Main topics
- integrated-project decomposition;
- signal and interface architecture;
- combining DSP, RF, and control logic;
- verification and test plan;
- project repository and documentation structure;
- system readiness criteria.

## Practical work
- assembling an end-to-end chain;
- documenting interfaces between modules;
- preparing verification scenarios;
- running integration tests.

## How to read this block: the lab map

This block has more than forty labs because it records a real bring-up of an in-fabric QPSK
modem on a Zynq-7020 + AD9361 board. **Not every lab is an exercise to repeat.** Some are the
working chronicle of debugging real hardware: they show how a problem is narrowed down, what
was tried and rejected, and how the diagnosis changed. Read those as case studies. Use the map
below to decide what to do and what to read.

| Stage | Labs | What you learn | Needs |
|---|---|---|---|
| 1. Define and simulate | [11.1](/zynq-sdr-course/en/labs/lab-11-1-project-requirements-and-architecture/) requirements and architecture, [11.2](/zynq-sdr-course/en/labs/lab-11-2-end-to-end-simulation-package/) end-to-end simulation package, [11.3](/zynq-sdr-course/en/labs/lab-11-3-fpga-rf-integration-checklist/) FPGA/RF integration and safety checklist, [11.5](/zynq-sdr-course/en/labs/lab-11-5-axi-dma-latency-jitter/) DMA latency/jitter model, [11.6](/zynq-sdr-course/en/labs/lab-11-6-measurement-uncertainty-budget/) uncertainty budget | turning a goal into requirements, a reproducible simulation, a safe path to RF, and honest reporting of measured numbers | software only |
| 2. Measure the finished modem (core) | [11.27](/zynq-sdr-course/en/labs/lab-11-27-runtime-qpsk-digital-loopback/) QPSK digital-loopback BER, [11.29](/zynq-sdr-course/en/labs/lab-11-29-cold-boot-ber-campaign/) cold-boot BER campaign, [11.4](/zynq-sdr-course/en/labs/lab-11-4-final-measurement-report/) final measurement report | how "the modem decodes" becomes a number with a confidence interval, and what a complete report looks like | board (read-only otherwise) |
| 3. Offline receive and packets | [11.38](/zynq-sdr-course/en/labs/lab-11-38-hardware-tx-iq-capture-offline-rx/) TX to IQ capture to offline receiver, [11.46](/zynq-sdr-course/en/labs/lab-11-46-two-board-console-message/) message between two boards | a full receiver in Python on a recorded capture, and packet framing | software (11.38 self-test), two boards (11.46) |
| 4. Bring-up chronicle | 11.7 to 11.19 (AXI-Lite bring-up, gpreg overlay, RF discovery, timed IIO snapshot, contention probe, stock-versus-runtime comparison, re-init probes, self-timed bring-up) | a worked example of narrowing down "the receive path sees nothing"; resolved in [11.26](/zynq-sdr-course/en/labs/lab-11-26-runtime-dds-bypass-bpsk-ota/) | board (case study) |
| 5. Independent monitoring with an RTL-SDR | [11.14](/zynq-sdr-course/en/labs/lab-11-14-stock-shell-bpsk-ota/) and 11.20 to 11.25, [11.28](/zynq-sdr-course/en/labs/lab-11-28-rtl-sdr-ota-qpsk/) | verifying a transmitter with a second, independent receiver | board + RTL-SDR |
| 6. Two-board carrier and timing story | 11.30 to 11.35 (coarse-CFO estimator on a real link, stress sweep, in-fabric acquisition, a rejected timing hypothesis, Gardner timing recovery, paired A/B) | carrier and timing recovery validated on hardware, including a hypothesis that was disproved | two boards (case study) |
| 7. The last few percent | 11.41 (DC blocker followed the data), 11.42 (frame-sync false lock), 11.45 (differential QPSK and a longer preamble) | how a residual error floor is traced to its cause, one layer at a time | two boards (case study) |

If you have **no hardware**, do stages 1 and 3 (the 11.38 self-test runs offline), and read stages 2
and 4 to 7 as case studies; the results they report are committed as JSON evidence under
`docs/assets/`. If you have **one board**, add stage 2. The two-board stages need two boards and a
controlled, attenuated cable path; see the RF-safety rules in Lab 11.3 before transmitting.

## Tooling for the block
The main toolset is: Simulink, Vivado, MATLAB, Python, KiCad.

## Expected outputs
- project architecture diagram;
- interface table;
- integration-test protocol;
- integrated report.

## Folder structure
```text
block_11_integrated_sdr_project/
├── README.md
├── README_ru.md
├── README_en.md
├── CONTENTS_ru.md
├── CONTENTS_en.md
├── assets/
├── images/
├── kicad/
├── simulink/
├── matlab/
├── python/
├── cpp/
├── gnuradio/
└── reports/
```

- `assets/` — reference data and helper materials;
- `images/` — diagrams, screenshots, and photos;
- `kicad/` — schematics and electrical notes;
- `simulink/`, `matlab/`, `python/`, `cpp/`, `gnuradio/` — models and analysis tools;
- `reports/` — reports and report templates.

## Recommended work order
1. split the project into subsystems.
2. align interfaces and data formats.
3. run integration tests.
4. prepare system documentation.

## Next step
After finishing this block, the student should be ready to reuse its results as the starting point for the next stage of the course and the related practical experiment.
