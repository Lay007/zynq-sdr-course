# Hardware Evidence Index

This page collects hardware-facing proof artifacts for the course. It is a navigation layer between educational labs and engineering evidence.

## Purpose

The course should not only explain SDR, DSP, fixed-point and HDL concepts. It should also show what was actually verified, what is still a template, and what requires a real board run.

Use the status values below:

| Status | Meaning |
|---|---|
| `template` | structure exists, no measured data yet |
| `synthetic` | reproducible simulation or generated data only |
| `measured` | real hardware or instrument result exists |
| `reviewed` | result has configuration, metadata, plots, metrics and limitations |

## Evidence map

| Evidence item | Path | Status | Notes |
|---|---|---|---|
| Block 5 FPGA evidence page | `docs/block5-fpga-evidence.md` | reviewed | nav-visible digest of the current Vivado evidence package |
| Block 5 HDL latency contract | `blocks/block_05_fpga_hdl_flow/hdl_latency_contract.md` | reviewed | observable valid/data timing contract for the smoke-tested HDL blocks |
| Z7020 OOC FPGA summary | `reports/fpga/z7020-resource-summary-template.md` | synthetic | first curated resource/timing snapshot with board clock provenance |
| Block 5 utilization summary | `reports/fpga/block5-utilization-summary.md` | synthetic | LUT/FF/DSP/BRAM usage for the four Block 5 HDL examples |
| Block 5 timing summary | `reports/fpga/block5-timing-summary.md` | synthetic | 100 MHz OOC timing snapshot and limits |
| Block 5 latency/throughput notes | `reports/fpga/block5-latency-throughput-notes.md` | reviewed | one-cycle behaviour and streaming-rate notes from HDL testbenches |
| Integrated SDR project labs | `docs/ru/labs/lab-11-7-axi-lite-bpsk-bringup.md` and following | synthetic | control-plane and burst-capture workflow now documented for lab execution |
| Block 11 hardware bring-up summary | `docs/block11-hardware-bringup-summary.md` | measured | compact tracker for current integrated SDR hardware state, blocker and next experiments |
| Clean-image Zynq RX observation manifest | `datasets/lab6_6_zynq_rx_observation/` | measured | first board-facing RX-only manifest package; keep reports and plots synchronized when new captures are added |
| Stock-shell Zynq OTA tone observation | `datasets/lab6_8_zynq_ota_tone_observation/` | reviewed | measured `915 MHz / 700 kHz` tone package with manifest, FFT plot, metrics JSON and conservative TX/RX settings |
| QPSK demo dataset manifest | `datasets/demo_qpsk_capture/manifest.yaml` | template | issue #26 should promote this from manifest-only to validated replay evidence |
| Hardware validation backlog | `docs/hardware-validation-backlog.md` | reviewed | issue-linked closure plan for #25, #26 and #29 |
| FPGA resource report template | `reports/fpga_resource_report.template.md` | template | use when extending the current package to a new design |
| Reviewer checklist | `docs/reviewer-checklist.md` | reviewed | general acceptance criteria |
| Reviewer one-page summary | `docs/reviewer-one-page-summary.md` | reviewed | short entry point for technical review and local checks |
| Real data policy | `docs/real-data-policy.md` | reviewed | prevents large binary data from bloating Git |
| Experiment manifests | `experiments/` | synthetic | machine-checkable scenario descriptors |
| IQ dataset descriptors | `datasets/` | template | use manifests and external storage when needed |
| Final project reports | `reports/` | template | connect model, implementation and measurement |

## Recommended hardware proof package

A mature hardware experiment should include:

```text
configuration notes
  -> dataset or capture manifest
  -> generated plots
  -> metrics table
  -> short engineering conclusion
  -> limitations and next action
```

Minimum files for one experiment:

| File | Purpose |
|---|---|
| `manifest.yaml` | settings, format, source and reproducibility metadata |
| `report.md` | human-readable explanation and conclusion |
| `summary.csv` | compact metrics table |
| `*.svg` or `*.png` | spectrum, time-domain, constellation or other plot |

## Open proof gaps

The strongest next artifacts are:

1. Routed top-level Vivado timing and utilization for the integrated Zynq design.
2. Issue #25 remainder: a safe cabled loopback capture report with attenuation notes.
3. Issue #26: a small validated QPSK dataset package.
4. Issue #29: an AD9363 gain and large-signal characterization table.
5. One final project report that connects model, HDL, capture and metrics.

## Review rule

A hardware result should not be marked as `reviewed` until another engineer can answer:

- what was configured;
- what was captured or built;
- what command or tool produced the artifacts;
- what metric was calculated;
- what conclusion follows;
- what is not proven yet.
