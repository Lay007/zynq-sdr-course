# Instructor guide

This page explains how to use the repository as a structured SDR/FPGA teaching workspace.

## 1. Choose the teaching mode

| Mode | Suitable when | Main pages |
|---|---|---|
| Theory + simulation only | no hardware is available yet | [DSP foundation track](dsp-foundation-track.md), [Lab index](lab-index.md), [Reproducibility guide](reproducibility-guide.md) |
| Fixed-point + HDL | students already know DSP basics | [DSP → FPGA Bridge](dsp-to-fpga.md), [CIC fixed-point FPGA bridge](cic-fixed-point-fpga-bridge.md) |
| Hardware-assisted SDR | a controlled board + receiver setup is available | [Hardware checklist](hardware-checklist.md), [RF safety guide](rf-safety.md), [SDR measurement report template](sdr-measurement-report-template.md) |

## 2. Recommended classroom flow

1. Start with the system view: [Model → FPGA → RF → Measurement](model-to-measurement.md).
2. Assign one or two DSP labs with generated plots.
3. Move to fixed-point and HDL only after the floating-point path is clear.
4. Introduce hardware only when RF safety, metadata and reporting discipline are already explained.
5. Finish with one end-to-end mini-project or measurement report.

## 3. Pre-class checklist

- the relevant docs pages build locally;
- required lab scripts run at least once;
- hardware assumptions are written down;
- students know what artifact they must produce;
- the acceptance criterion is visible before the lab starts.

## 4. What good student output looks like

A strong lab submission should contain:

- one reproducible command path;
- one figure or report;
- one short engineering conclusion;
- configuration notes for any hardware-facing step.

The repository already provides templates and guides for that discipline:

- [Lab report template](lab-report-template.md)
- [SDR measurement report template](sdr-measurement-report-template.md)
- [IQ recording metadata guide](iq-recording-metadata.md)
- [Measurement uncertainty guide](measurement-uncertainty-guide.md)

## 5. Safety and evidence discipline

Before any RF lab, require students to read:

1. [Hardware checklist](hardware-checklist.md)
2. [RF safety guide](rf-safety.md)
3. [Real data policy](real-data-policy.md)

This prevents labs from turning into undocumented "it worked on the bench" demos.

## 6. Useful pages for course maintenance

- [Course status](status.md)
- [Course quality roadmap](course-quality-roadmap.md)
- [Course readiness matrix](course-readiness-matrix.md)
- [Course quality gates](course-quality-gates.md)
- [Contributing labs](contributing-labs.md)

These pages are the maintenance backbone for keeping the course coherent as it grows.
