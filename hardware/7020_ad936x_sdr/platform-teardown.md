# 7020 AD936x platform teardown

This page applies the SDR platform teardown template to the course hardware baseline.

The purpose is to give students a system-level view before they start changing registers, HDL or RF settings.

## Platform summary

| Field | Course baseline |
|---|---|
| Board class | Zynq-7020 SDR board family used by the course. |
| RF frontend | AD9363 / AD936x-compatible transceiver path. |
| Digital device | Zynq-7000 processing system plus programmable logic. |
| Host interface | Linux userspace, IIO-style tooling, local scripts and optional network access. |
| FPGA role | Streaming DSP, counters, AXI-Lite control, packet/BER experiments. |
| Observation helper | RTL-SDR or another receiver can be used as an independent monitor. |

## System layers

```text
RF connector
  -> matching / board RF path
  -> AD936x RF frontend
  -> sample interface
  -> Zynq programmable logic
  -> AXI / memory / control plane
  -> processing system scripts
  -> IQ capture and offline analysis
```

This is the practical version of the course route:

```text
model -> fixed-point -> HDL -> Zynq -> RF frontend -> capture -> report
```

## RF frontend notes

For course use, the most important AD936x topics are:

- center frequency and sample-rate planning;
- analog and digital gain settings;
- receive bandwidth and filtering;
- zero-IF artifacts such as DC component and IQ imbalance;
- calibration state and repeatability;
- safe starting settings for cabled experiments.

Students should not treat RF frontend settings as a black box. A small gain or bandwidth change can change the measured result, even when the DSP model is unchanged.

## FPGA and control-plane role

The programmable logic is used as the place where timing becomes explicit:

| Layer | Course role |
|---|---|
| Streaming RTL | FIR, mixer, BPSK blocks and AXI-Stream wrappers. |
| AXI-Lite registers | Start, status, counters and reproducible bring-up checks. |
| Testbenches | Latency, throughput and reference-vector comparison. |
| Hardware reports | Timing, utilization and implementation evidence. |

The processing system is used for configuration, data movement, register access and report generation. It is not a substitute for deterministic HDL verification.

## Transport and buffering risks

A working SDR chain can still fail because of system-level effects:

- buffers are too small for the selected sample rate;
- Linux scheduling changes the timing of short control actions;
- a capture starts too early or too late relative to a burst;
- the RF frontend is tuned correctly but gain or bandwidth hides the signal;
- a register-level done flag is observed, but the recovered data is still empty.

These risks are why the course records manifests, commands, plots and limitations for every mature experiment.

## Safe starting procedure

Before a cabled board-level experiment:

1. start from the documented clean image or known-good project snapshot;
2. use the lowest practical output level;
3. insert an attenuator in the cabled path;
4. record frequency, sample rate, bandwidth and gain values;
5. capture a short IQ file first;
6. inspect time domain and spectrum before increasing levels;
7. save the command and metadata with the result.

## Evidence target

A platform result should eventually produce:

| Artifact | Purpose |
|---|---|
| `manifest.yaml` | Settings, format, command and capture context. |
| `report.md` | Human-readable setup, result and limitations. |
| `summary.csv` | Compact metrics table. |
| `*.png` or `*.svg` | Spectrum, time-domain, constellation or BER/EVM figure. |

This page should be updated when the board baseline, image, bitstream or measurement procedure changes.
