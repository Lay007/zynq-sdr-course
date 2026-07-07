# Block 11 Hardware Bring-up Summary

This page keeps detailed Block 11 hardware notes separate from the top-level course status matrix.

## Purpose

Block 11 is the integrated SDR project track. Its goal is to connect the reference model, fixed-point and HDL handoff, board-side implementation, capture evidence, metrics and final report.

## Current evidence map

| Evidence | Current state | Notes |
|---|---|---|
| Baseline board path | reviewed | The vendor Linux/IIO path is the known-good reference. |
| External monitor flow | measured | WAV/IQ monitor capture and offline replay are documented. |
| Connected RTL-SDR witness | measured | 868.3 MHz stock DDS tone measured at +201.965 kHz, SNR 40.30 dB, no clipping. |
| Fallback reference path | reviewed | The fallback path has a zero-error reference result. |
| Runtime overlay control path | reviewed | Register readback and re-init helpers show that the overlay is alive after reload. |
| Runtime on-chip loopback | measured | The promoted loopback point reaches zero errors for the current deterministic frame. |
| QPSK RTL and bridge path | executable | Canonical simulation reaches BER=0 for 140 symbols / 280 bits through the dual-modem bridge. |
| Runtime QPSK fabric loopback | measured | Timing-clean payload: 4/4 boot sessions and 13/13 attempts at offset 62 reached BER=0 for 140 symbols / 280 bits. |
| Integrated FPGA implementation | measured signoff candidate | Hardware-correlated snapshot is fully routed with WNS +0.003 ns and passes the QPSK fabric qualification; timing margin remains narrow. |
| External measured proof package | hardware pending | The remaining step is a repeatable measured package with matched settings, metadata, plots and limitations. |

## Status alignment note

The earlier version of this page described an old blocker with high error rate and run-to-run variability. The top-level status matrix has since been promoted: the current internal loopback result is measured, while the remaining work is external measurement packaging and repeatability.

## Remaining engineering statement

> The runtime path has a measured zero-error internal loopback result. The next proof is to make the same story reviewer-friendly at the measurement level: setup notes, manifest-backed capture, generated plots, metrics and a short limitations section.

## Next experiments

| Priority | Experiment | Expected evidence |
|---|---|---|
| Done | Repeat the promoted loopback point from a clean boot | 4/4 clean boot sessions and 13/13 attempts on the timing-clean payload |
| P0 | Add a controlled cabled measurement variant | attenuation, gain settings and metric table |
| P1 | Compare baseline and runtime captures with matched monitor settings | paired manifests, plots and conclusions |
| P1 | Improve timing-closure margin | repeat builds or seed sweep with stable positive WNS |
| P2 | Extend QPSK from digital loopback to measured RF | dataset manifest, constellation, EVM/SNR and BER summary |
| P2 | Promote the best result into a final project report | model-to-measurement report with limitations |

## Done criteria

Block 11 should become `Portfolio-ready` only when it has a clean command path, manifest-backed data, configuration notes, plots, BER/EVM/SNR metrics, a short conclusion and an explicit limitations section.

## Related pages

- [Hardware evidence index](hardware-evidence-index.md)
- [Hardware validation backlog](hardware-validation-backlog.md)
- [End-to-end BPSK reference report](end-to-end-bpsk-reference-report.md)
- [End-to-end QPSK hardware demo](end-to-end-qpsk-hardware-demo.md)
