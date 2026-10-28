# Frequently asked questions

Short answers for first-time readers. Detailed procedures and measured results remain in the [course website](https://lay007.github.io/zynq-sdr-course/).

## Do I need Zynq hardware to start?

No. Start with the Python DSP and fixed-point exercises. Add an RTL-SDR for independent observation, then Zynq/AD936x and controlled RF experiments when the corresponding labs require them. See [learning routes](https://github.com/Lay007/zynq-sdr-course/blob/main/LAB_TRACK_en.md) and [Getting Started](Getting-Started).

## Is MATLAB/Simulink mandatory?

No. Several modeling labs also have Python paths. MATLAB/Simulink helps demonstrate the model-to-fixed-point workflow, but not every lab requires a MATLAB license. Check the prerequisites of the specific lab in the [course README](https://github.com/Lay007/zynq-sdr-course/blob/main/README.md).

## Which board and tools are expected?

The hardware track targets Zynq-7020-class SDR boards with AD936x-class RF frontends, plus tools such as Vivado and an optional independent RTL-SDR. Exact clocking, interfaces, images and front-end capabilities vary by board. Consult [Hardware](Hardware) and the [board README](https://github.com/Lay007/zynq-sdr-course/blob/main/hardware/7020_ad936x_sdr/README.md).

## What is the difference between a DSP model and an RTL implementation?

A reference model primarily checks algorithm behavior. Fixed-point work establishes numerical limits and scaling; RTL checks cycle and handshake behavior; FPGA implementation adds timing/resource constraints; RF experiments add analog effects and clock offsets. See [Architecture](Architecture) and [DSP to FPGA](DSP-to-FPGA).

## Why does a modem pass fabric loopback but show high BER through RF?

Fabric loopback removes many analog and synchronization effects. A real RF path adds receiver gain issues, oscillator offsets, filtering, sample timing error and possible front-end overload. Confirm preamble detection, CFO, timing, I/Q mapping and capture alignment before changing the algorithm. Start from [Troubleshooting](Troubleshooting) and the [digital-link metrics guide](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/digital-link-metrics.md).

## Does BER = 0 mean the link is error-free?

No. It means **zero bit errors among the compared bits under the stated test conditions**. Always include the bit count, number of frames/bursts, detector success rate and conditions. The approximate 95% rule-of-three limit for zero observed errors under independent trials is `BER < 3/N`; it is not proof of zero BER in service. See [metric definitions](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/digital-link-metrics.md).

## Is SNR obtained from EVM equivalent to a calibrated RF SNR?

Not necessarily. An EVM-derived SNR estimate only tracks true SNR under assumptions such as uncorrelated additive noise and correct synchronization. The course labels this distinction explicitly. See [Digital-link metric calculations](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/digital-link-metrics.md).

## Why are dBFS and dBm different?

dBFS describes a level relative to a digital full-scale reference, while dBm is power relative to 1 mW. Converting between them requires a calibrated measurement chain and specified impedance/reference; a raw ADC value alone cannot provide an absolute received power. See [course measurement guides](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/measurement-uncertainty-guide.md).

## How do I know whether a result was actually measured?

Open the [Hardware evidence index](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/hardware-evidence-index.md). Check whether the result is synthetic, HDL/FPGA-validated or measured and whether an original report gives settings, data, sample counts and limitations.

## Why does an IQ dataset file look very small?

It may be a Git LFS pointer rather than the recording. Run `git lfs install` and `git lfs pull`, then inspect the metadata and file format. See the [IQ metadata guide](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/iq-recording-metadata.md).

## Where should I ask a question or report a problem?

Read [Support](https://github.com/Lay007/zynq-sdr-course/blob/main/SUPPORT.md) first. General learning questions belong in [Discussions](https://github.com/Lay007/zynq-sdr-course/discussions); use an Issue for a reproducible defect or a specific improvement. Do not publish credentials, private IQ captures or sensitive vulnerabilities.

## Can I add a new laboratory exercise?

Yes. Explain the learning goal, runnable experiment, expected artifacts, checks and evidence level. Follow [Contributing](https://github.com/Lay007/zynq-sdr-course/blob/main/CONTRIBUTING.md) and the [lab contribution guide](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/contributing-labs.md).

[Home](Home) · [Architecture](Architecture) · [Troubleshooting](Troubleshooting)
