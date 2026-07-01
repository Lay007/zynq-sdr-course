# Block 11 Hardware Bring-up Summary

This page keeps detailed Block 11 hardware notes separate from the top-level course status matrix.

## Purpose

Block 11 is the integrated SDR project track. Its goal is to connect the reference model, fixed-point and HDL handoff, Zynq PL path, AD9363 RF path, external monitor capture, metrics and final report.

## Current evidence map

| Evidence | Current state | Notes |
|---|---|---|
| Stock-shell AD9363 path | measured | The baseline Linux/IIO path is the known-good reference. |
| RTL-SDR monitor flow | measured | WAV/IQ monitor capture and offline BER replay are documented. |
| Stock-shell BPSK fallback | reviewed | The fallback path has a zero-BER reference result. |
| Runtime PL BPSK path | measured | The runtime path is visible in monitor captures, but BER robustness is still open. |
| Runtime overlay control path | partially proven | Register readback and re-init helpers show that the overlay is alive after reload. |

## Current blocker

The remaining Block 11 problem is not simply missing visibility of the runtime path. The better engineering statement is:

> The runtime PL BPSK path is observable, but the recovered frame still has high BER and run-to-run variability. The next step is to make acquisition, timing and gain settings repeatable from a clean boot.

## Next experiments

| Priority | Experiment | Expected evidence |
|---|---|---|
| P0 | Repeat the promoted runtime monitor point from a clean boot | manifest, metrics JSON, BER table, conclusion |
| P0 | Sweep acquisition prefix, decision axis and start offset | ranked table and best-point rerun |
| P1 | Add a cabled attenuated loopback variant | RF notes, attenuation, gain settings and BER/EVM metrics |
| P1 | Compare stock-shell and runtime captures with matched monitor settings | paired manifests and plots |
| P2 | Promote the best result into a final project report | model-to-measurement report with limitations |

## Done criteria

Block 11 should become `Portfolio-ready` only when it has a clean command path, manifest-backed IQ data, RF configuration notes, plots, BER/EVM/SNR metrics, a short conclusion and an explicit limitations section.

## Related pages

- [Hardware evidence index](hardware-evidence-index.md)
- [Hardware validation backlog](hardware-validation-backlog.md)
- [End-to-end BPSK reference report](end-to-end-bpsk-reference-report.md)
- [End-to-end QPSK hardware demo](end-to-end-qpsk-hardware-demo.md)
