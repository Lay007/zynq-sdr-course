# DSP to FPGA

The central engineering problem is preserving the **observable behavior** of a signal-processing algorithm while translating it from a numerical model into an implementation with finite precision, latency and resource constraints.

## Verification ladder

| Stage | What to check | Evidence |
| --- | --- | --- |
| Reference DSP model | Inputs, expected spectrum, algorithm assumptions and normalization | Deterministic vectors, reference plots |
| Fixed-point model | Word lengths, scaling, rounding, saturation/wrap, error against float | Error statistics and numeric format |
| RTL simulation | Bit-true behavior, reset, latency, valid/ready handling, framing | Self-checking testbench and logs |
| FPGA implementation | Timing closure, resource use, clocks and CDC | Vivado timing/utilization reports |
| RF experiment | Gain, sample rate, synchronization, overload and channel effects | Capture metadata, spectrum, EVM/BER or other metric |
| Engineering conclusion | What was proven, under which conditions, and what remains unknown | Versioned report with limitations |

The detailed narrative is in [DSP → FPGA Bridge](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/dsp-to-fpga.md) and [Model → FPGA → RF → Measurement](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/model-to-measurement.md).

## Practical handoff contract

Before generating or hand-writing HDL, state:

- Input/output sample formats, scaling and interpretation of I/Q.
- Sample and symbol rates, interpolation/decimation factors and clock assumptions.
- Pipeline latency, throughput, reset behavior and backpressure handling.
- Coefficient and internal accumulator widths, overflow policy and quantization points.
- Golden input/output vectors, tolerances and exactly which checks are bit-exact.
- Expected FPGA resources and timing constraints.

An acceptable floating-point waveform does not imply that the fixed-point design has sufficient headroom. A correct RTL simulation does not imply that the routed FPGA meets timing.

## Reproducible local checks

```bash
python tools/tasks.py labs
python tools/tasks.py hdl
```

For source-level verification details, read [HDL smoke verification](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/verification/hdl_smoke.md). Its checks are deliberately smaller than full timing closure or board qualification.

## PS/PL interface questions

- **AXI4-Lite:** control registers and status.
- **AXI4-Stream:** ordered payload samples, timing and backpressure.
- **DMA:** transfer data between PS memory and the streaming datapath.

Check ownership of reset, clocks, `tvalid`/`tready` and buffer boundaries before treating a data-path failure as a DSP algorithm defect. Start with [Zynq PS/PL architecture](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/zynq-ps-pl-architecture.md) and the [student path](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/student-path.md).

## Reporting rules

Always distinguish **model result**, **fixed-point comparison**, **RTL simulation**, **FPGA timing/board test** and **RF measurement**. Record counts alongside metrics: `BER = 0` without the number of compared bits is incomplete evidence.

For metric definitions and caveats, see [Digital-link metric calculations](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/digital-link-metrics.md). For current hardware claims, follow the [evidence index](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/hardware-evidence-index.md).

[Getting Started](Getting-Started) · [Hardware](Hardware) · [Troubleshooting](Troubleshooting)
