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
| Z7020 OOC FPGA summary | `reports/fpga/z7020-resource-summary-template.md` | synthetic | first curated resource/timing snapshot with board clock provenance |
| Block 5 utilization summary | `reports/fpga/block5-utilization-summary.md` | synthetic | LUT/FF/DSP/BRAM usage for the four Block 5 HDL examples |
| Block 5 timing summary | `reports/fpga/block5-timing-summary.md` | synthetic | 100 MHz OOC timing snapshot and limits |
| Block 5 latency/throughput notes | `reports/fpga/block5-latency-throughput-notes.md` | reviewed | one-cycle behaviour and streaming-rate notes from HDL testbenches |
| FPGA resource report template | `reports/fpga_resource_report.template.md` | template | use when extending the current package to a new design |
| Reviewer checklist | `docs/reviewer-checklist.md` | reviewed | general acceptance criteria |
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
2. A small validated QPSK dataset manifest.
3. A tone or loopback capture report.
4. A gain/overload characterization table.
5. One final project report that connects model, HDL, capture and metrics.

## Review rule

A hardware result should not be marked as `reviewed` until another engineer can answer:

- what was configured;
- what was captured or built;
- what command or tool produced the artifacts;
- what metric was calculated;
- what conclusion follows;
- what is not proven yet.
