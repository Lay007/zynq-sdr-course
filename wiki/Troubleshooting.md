# Troubleshooting

Start from the **first failing layer**. Fixing a later symptom can conceal the original defect. This table points to diagnostic checks; it is not a claim that every symptom has the same cause.

## Fast diagnosis

| Symptom | First checks | Canonical reference |
| --- | --- | --- |
| `iverilog` or `vvp` not found | Confirm Icarus installation and PATH; rerun only the HDL check | [HDL smoke verification](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/verification/hdl_smoke.md) |
| Recorded IQ file is tiny or looks like text | Check for Git LFS pointer; run `git lfs pull`; verify format and metadata | [IQ metadata](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/iq-recording-metadata.md) |
| Strict MkDocs build fails | Read the first broken link or anchor warning; fix its source path | [Reproducibility guide](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/reproducibility-guide.md) |
| Python lab differs from the expected plot | Verify seed, sample rate, FFT window, normalization and dependency versions | [DSP foundation](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/dsp-foundation-track.md) |
| RTL output differs from fixed-point reference | Check signedness, width, truncation, rounding, saturation, valid/ready and latency alignment | [DSP to FPGA](DSP-to-FPGA) |
| Vivado run fails or timing is negative | Inspect actual build logs, memory use, constraints, clock domains, pipeline and critical path | [FPGA evidence](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/block5-fpga-evidence.md) |
| No expected RF tone or capture | Verify board boot, loaded image, source enable, frequency plan, TX port, gain and RX settings | [Hardware bring-up](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/hardware-bringup-checklist.md) |
| BER high despite a working digital loopback | Compare preamble/frame detection, CFO, timing recovery, phase, IQ mapping and RF gain | [Digital-link metrics](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/digital-link-metrics.md) |
| Unexpected wideband products or clipped IQ | Stop and reduce input level; inspect attenuation, gain, ADC clipping and analog compression | [RF safety guide](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/rf-safety.md) |
| Result changes with AGC or between boards | Record AGC mode, capture timing and independent oscillator offsets; reproduce a controlled baseline | [Hardware evidence index](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/hardware-evidence-index.md) |

## Isolation sequence for a modem problem

1. Reproduce with a deterministic synthetic input.
2. Run fixed-point and RTL checks with the **same** input and alignment.
3. Confirm the target bitstream, control-plane settings and PS/PL transfer contract.
4. Test in fabric loopback before introducing the analog RF path.
5. Introduce a protected conducted RF path, capturing IQ and gain/clock settings.
6. Compare detected frames, CFO, EVM, BER and error counts, not only one headline metric.

Record the precise stage at which the result changes. Do not label a simulation result as an RF validation.

## Case: QPSK works in the FPGA but fails over the RF link

Start from a known-good HDL vector and **record the first new failing stage**.

| Observation | Next check |
| --- | --- |
| RTL vector mismatch | Alignment, bit ordering, word widths, rounding/saturation and ready/valid timing |
| Fabric loopback passes, no RF energy seen | Loaded bitstream, clocks, source enable, TX port, gain settings and external receiver |
| RF energy present, no frame lock | Frequency plan, sample rate, preamble correlation, input levels and CFO |
| Frame lock found, payload BER high | Residual CFO/phase, sampling/timing recovery, I/Q polarity, DC blocking and AGC transients |
| Only some bursts fail | Capture the full burst distribution and inspect per-burst diagnostics; do not report only the best frame |

For the project-specific QPSK DC blocker defect and its evidence, see [issue #66](https://github.com/Lay007/zynq-sdr-course/issues/66). For safe RF configuration and measurement definitions use the [RF safety guide](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/rf-safety.md) and [digital-link metrics](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/digital-link-metrics.md). A diagnosis is a hypothesis until verified against a reproducible capture or run.

## Case: PS/PL path responds but payload data is wrong

Check the AXI4-Lite control contract independently from the streaming data contract. Inspect register offsets, endianness, reset sequencing, the sample buffer size, DMA ownership, `tvalid`/`tready` and hardware/software version matching. A working control mailbox alone does not validate the IQ sample path.

See [PS/PL architecture](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/zynq-ps-pl-architecture.md) and [mailbox bring-up](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/zynq-ps-pl-mailbox-vivado-bringup.md).

## Collect a useful issue report

```text
Environment: OS, Python/tool versions, board revision
Revision: repository commit SHA and bitstream/build ID
Expected result:
Observed result and full error text:
Reproduction command and steps:
Clocking / sample rates / RF path, gain, attenuation:
Logs, plots, IQ metadata (if relevant):
What was already checked:
```

Avoid uploading private network details or large raw IQ recordings; provide sanitized logs and manifests. If a hardware receiver may be overloaded, stop transmission before collecting more data.

[Hardware](Hardware) · [DSP to FPGA](DSP-to-FPGA) · [Repository issues](https://github.com/Lay007/zynq-sdr-course/issues)
