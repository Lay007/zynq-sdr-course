# Zynq SDR Course — Engineering Wiki

A task-oriented reference for engineers and students working with SDR, DSP, fixed-point arithmetic, Verilog, Zynq-7020 and AD936x hardware.

**The [course website](https://lay007.github.io/zynq-sdr-course/) is the source of truth for lessons, laboratory procedures, measurement reports and verified results.** This Wiki is a short entry point: find the relevant diagnostic workflow here, then follow the linked course material for complete details.

## Choose your starting point

| Your task | Start here |
| --- | --- |
| Set up a laptop and run the first labs | [Getting Started](Getting-Started) |
| Identify boards, receivers, safe RF paths and bring-up checks | [Hardware](Hardware) |
| Move a DSP model through fixed-point and HDL to the board | [DSP to FPGA](DSP-to-FPGA) |
| Diagnose an installation, simulation, timing or RF problem | [Troubleshooting](Troubleshooting) |
| Follow the complete learning sequence | [Student path](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/student-path.md) |
| Review measured results and their limitations | [Hardware evidence index](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/hardware-evidence-index.md) |

## The engineering loop

```text
Reference model → Fixed-point model → RTL / testbench → FPGA
       → RF experiment → IQ capture → Analysis → Engineering decision
```

A passing simulation is not an RF measurement. An FPGA timing report is not proof of a working radio link. Keep the validation stage, experiment settings and evidence attached to every result.

Read the complete [Model → FPGA → RF → Measurement guide](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/model-to-measurement.md) and the [course status matrix](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/status.md).

## Learning routes

The course supports a laptop-only route as well as progressive routes using RTL-SDR, a Zynq/AD936x board and bench instruments. Pick a route according to the equipment available; do not start with RF transmission just to run the introductory labs.

See [Learning routes](https://github.com/Lay007/zynq-sdr-course/blob/main/LAB_TRACK_en.md) and [Course structure](https://github.com/Lay007/zynq-sdr-course/blob/main/COURSE_STRUCTURE_en.md).

## How this Wiki is maintained

- Keep procedures brief and link to the canonical course page or reproducible report.
- Distinguish **synthetic**, **RTL-tested**, **FPGA-tested**, **RF-measured** and **not yet tested** results.
- Do not copy lab instructions or changing measurement figures into Wiki pages.
- Store reviewable Wiki sources in the main repository's [`wiki/` directory](https://github.com/Lay007/zynq-sdr-course/tree/main/wiki).
- For corrections to course content, use the normal repository pull-request workflow.

[Repository](https://github.com/Lay007/zynq-sdr-course) · [Course website](https://lay007.github.io/zynq-sdr-course/) · [Contributing](https://github.com/Lay007/zynq-sdr-course/blob/main/CONTRIBUTING.md)
