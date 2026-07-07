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
| External QPSK RTL-SDR path | measured multi-burst | Promoted OTA run detects 30/30 bursts with 0/8,400 bit errors, median EVM 21.32%, median CFO +1.964 kHz and no clipping. |

## Status alignment note

The earlier version of this page described an old blocker with high error rate and run-to-run variability. The internal loopback and one 30-burst external session are now measured; the remaining work is cross-session/cabled validation, raw-data publication and timing margin.

## Remaining engineering statement

> The runtime path now has repeated zero-error internal loopback and a manifest-backed 30/30 external RTL-SDR burst series. The next proof is repetition across independent boots and a controlled cabled path.

## Next experiments

| Priority | Experiment | Expected evidence |
|---|---|---|
| Done | Repeat the promoted loopback point from a clean boot | 4/4 clean boot sessions and 13/13 attempts on the timing-clean payload |
| P0 | Add a controlled cabled measurement variant | attenuation, gain settings and metric table |
| P1 | Compare baseline and runtime captures with matched monitor settings | paired manifests, plots and conclusions |
| P1 | Improve timing-closure margin | repeat builds or seed sweep with stable positive WNS |
| Done | Extend QPSK from digital loopback to measured RF | OTA manifest, constellation, EVM/SNR and BER summary |
| Done | Measure external QPSK burst repeatability | 30/30 detected zero-error bursts with BER/EVM/CFO distributions and confidence bounds |
| P1 | Repeat QPSK across independent RF sessions | per-session burst statistics and cross-session variance |
| P2 | Promote the best result into a final project report | model-to-measurement report with limitations |

## Done criteria

Block 11 should become `Portfolio-ready` only when it has a clean command path, manifest-backed data, configuration notes, plots, BER/EVM/SNR metrics, a short conclusion and an explicit limitations section.

## Related pages

- [Hardware evidence index](hardware-evidence-index.md)
- [Hardware validation backlog](hardware-validation-backlog.md)
- [End-to-end BPSK reference report](end-to-end-bpsk-reference-report.md)
- [End-to-end QPSK hardware demo](end-to-end-qpsk-hardware-demo.md)
