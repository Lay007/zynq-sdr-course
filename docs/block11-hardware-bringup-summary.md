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
| Runtime QPSK fabric loopback | measured | CDC-fixed payload: 4/4 boot sessions and 13/13 attempts at offset 62 reached BER=0; selected ExtraTiming payload: 10/10 attempts reached BER=0 for 140 symbols / 280 bits. |
| Integrated FPGA implementation | measured signoff candidate | Hardware-correlated snapshot is fully routed; strategy sweep selected `Performance_ExtraTimingOpt` with WNS +0.096 ns, TNS 0 and 0 failing endpoints. |
| External QPSK RTL-SDR path | measured cross-session | Three independent OTA sessions detect 90/90 bursts with 0/25,200 bit errors, median EVM 19.04%, median CFO +1.969 kHz and no clipping. |
| Final two-board differential QPSK link | reviewed | Board A → 30 dB → board B in-fabric RX. Differential coding plus a 24-symbol preamble remove every whole-burst rotation failure (gross 0) at payload BER 4.45×10⁻⁴ over 800 frames; fabric loopback stays at BER < 5.34×10⁻⁷ over 5.6 M bits. The shipped differential image closes timing at WNS +0.036 ns — a separate build from the WNS +0.096 ns canonical strategy sweep above. Lab 11.4 is the final measurement report; Labs 11.41–11.45 carry the investigation. |

## Status alignment note

The earlier version of this page described an old blocker with high error rate and run-to-run variability. The internal loopback and three 30-burst external sessions are now measured. A 2026-07-08 implementation-strategy sweep improved the canonical routed snapshot to WNS +0.096 ns and the selected payload passed fabric loopback. The integrated modem is now closed on a two-board differential link (see the evidence map above); the remaining work is repeat-build/seed timing robustness, raw-data publication and stable long-run external capture.

## Remaining engineering statement

> The integrated modem is now closed on a two-board 915 MHz RF link: differential coding plus a 24-symbol preamble give zero whole-burst rotation failures at payload BER 4.45×10⁻⁴, on top of repeated zero-error fabric loopback and a manifest-backed 3/3-session external RTL-SDR baseline. The remaining proofs are optional hardening: repeat-build/seed timing robustness, publication of the measured raw WAV, and longer-duration external statistics.

## Next experiments

| Priority | Experiment | Expected evidence |
|---|---|---|
| Done | Repeat the promoted loopback point from a clean boot | 4/4 clean boot sessions and 13/13 attempts on the timing-clean payload |
| Done | Add a controlled cabled measurement variant | two-board SMA + 30 dB link with attenuation, gain settings and the Lab 11.4 metric table |
| P1 | Compare baseline and runtime captures with matched monitor settings | paired manifests, plots and conclusions |
| Done | Improve timing-closure margin with implementation strategies | 6/6 timing-clean runs, selected WNS +0.096 ns and timing-sweep plot/report |
| P1 | Verify repeat-build/seed timing robustness | repeat builds or seed sweep retain stable positive WNS |
| Done | Extend QPSK from digital loopback to measured RF | OTA manifest, constellation, EVM/SNR and BER summary |
| Done | Measure external QPSK burst repeatability | 30/30 detected zero-error bursts with BER/EVM/CFO distributions and confidence bounds |
| Done | Repeat QPSK across independent RF sessions | 3/3 sessions, 90/90 bursts, 0/25,200 bits and safe stock restore |
| P1 | Stabilize long RTL-SDR capture | strict longer series detects all commanded bursts or uses a more stable capture backend |
| Done | Promote the best result into a final project report | Lab 11.4 model-to-measurement report with pass/fail table and limitations |

## Done criteria

Block 11 should become `Portfolio-ready` only when it has a clean command path, manifest-backed data, configuration notes, plots, BER/EVM/SNR metrics, a short conclusion and an explicit limitations section.

## Related pages

- [Hardware evidence index](hardware-evidence-index.md)
- [Hardware validation backlog](hardware-validation-backlog.md)
- [End-to-end BPSK reference report](end-to-end-bpsk-reference-report.md)
- [End-to-end QPSK hardware demo](end-to-end-qpsk-hardware-demo.md)
