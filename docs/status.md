# Course status and readiness matrix

This page is the compact top-level engineering status board for the course. It shows what is already strong, what is executable, and what still needs hardware validation.

Detailed bring-up logs should live on dedicated evidence pages rather than inside this matrix.

## Readiness legend

| Mark | Meaning |
|---|---|
| `Ready` | Stable learner-facing material. |
| `Executable` | Scripts, tests, plots or reproducible checks exist. |
| `Measured` | Real hardware or IQ capture evidence exists. |
| `Hardware pending` | Board-level validation or real capture data is still needed. |
| `Portfolio-ready` | Documentation, reproducible artifacts and reviewer-friendly evidence are present. |

## Quick decodings

| Term | Meaning here |
|---|---|
| `stock-shell` | The board's normal vendor Linux and PL baseline after boot. |
| `runtime overlay` | A PL payload loaded after Linux boot for course experiments. |
| `BPSK` | Binary phase-shift keying. |
| `CSS` | Chirp spread spectrum; the current labs implement an educational waveform and detector, not yet a complete LoRa packet PHY. |
| `evidence` | A manifest, JSON report, plot or log proving the result. |

## Block readiness matrix

| Block | Topic | Current state | Evidence level | Main gap / next improvement |
|---|---|---|---|---|
| 01 | Intro to SDR | Ready | Real RTL-SDR captures and controlled Zynq tone witness | Add a short learner report comparing passive capture and controlled tone. |
| 02 | Signals and sampling | Executable | Python labs and generated figures | Add MATLAB/C++ translations and metadata-mistake replay examples. |
| 03 | DSP basics | Executable | Python / MATLAB / C++ path | Add direct-vs-FFT convolution threshold demo and more reference outputs. |
| 04 | Simulink and fixed-point | Executable | Python/MATLAB references and BPSK `.slx` models | Constrain the BPSK Simulink path further for HDL Coder handoff. |
| 05 | FPGA / HDL flow | Measured signoff candidate | The canonical suite now includes 34 HDL tests. The payload-telemetry image is fully routed at WNS +0.009 ns / WHS +0.028 ns, clean-boots on board B and produces a live preamble/payload split. | Add payload error-position telemetry, then challenge repeat-build/seed stability. |
| 06 | RF frontend and AD9363 | Measured | RX-only, OTA tone, protected conducted-tone baseline, first relative gain table, and a measured 30 dB attenuator flat from 50 MHz to 1 GHz | Measure cable loss separately, repeat the table across frequency and establish a connector-to-connector large-signal limit. |
| 07 | TX/RX chains | Executable | DUC/DDC demos and loopback models | Add measurement package. |
| 08 | Modulation and synchronization | Executable | CFO, timing, BER/EVM, OFDM mini-link, OFDM PAPR/clipping and CSS dechirp/FFT models with CI metric gates | Add packet-level CSS synchronization, LoRa interoperability evidence and FPGA implementations. |
| 09 | Recording and analysis tools | Measured | CI16/CU8/CF32/WAV readers, fail-closed manifest CI and QPSK multi-burst BER/EVM/CFO analysis | Publish or externally archive the raw QPSK WAV. |
| 10 | KiCad and basic electronics | Draft | Calculators and templates | Add measured breadboard photos and KiCad exports. |
| 11 | Integrated SDR project | Paired continuous timing measured; baseline retained | Lab 11.35 records 1,200 interleaved pairs, diagnoses the axis-sign TED, rejects the dot-product replacement at the focused clean gate, then localizes all 55 single-bit Gardner misses in a 160-pair instrumentation run to payload rather than preamble. Gardner still raises lock to 146/160 and lowers payload BER to 0.073523, but yields only 4/160 clean attempts versus 44/160 fixed. | Record first/last or segmented payload error positions to distinguish within-frame drift from uniform decision-margin loss. |
| 12 | Final projects | Measured cross-session example | Filled report plus internal QPSK qualification and three-session external OTA baseline | Add calibrated cabled and longer-duration statistics on a stable capture backend. |

## Hardware validation priorities

| Priority | Task | Done when |
|---|---|---|
| P0 | Safe cabled loopback | Attenuation, gain settings, capture metadata and short conclusion are recorded. |
| P0 | Runtime PL BPSK/QPSK robustness | Success count / total attempts is repeatable from clean boot and reported with limitations. |
| P1 | QPSK demo dataset | Manifest, checksum or immutable link, constellation, EVM/SNR and replay command exist. |
| P1 | Digital-link metric gate | Digital labs report SNR/EVM plus BER or FER with compared bit/frame count. |
| P1 | AD9363 gain table | Gain settings, clipping/SNR behavior and safe starting values are documented. |
| P2 | OFDM/CSS hardware evidence | Digital loopback, safe RF path, configuration metadata, EVM plus BER/SER/PER and limitations are recorded. |
| P2 | Final hardware report | One report connects model, HDL, capture, metrics and engineering conclusion. |

## Evidence and backlog pages

- [Hardware evidence index](hardware-evidence-index.md)
- [Hardware validation backlog](hardware-validation-backlog.md)
- [Block 11 hardware bring-up summary](block11-hardware-bringup-summary.md)
- [Reviewer acceptance checklist](reviewer-checklist.md)
- [Course quality roadmap](course-quality-roadmap.md)
- [Release checklist](release-checklist.md)

## Current release focus

The next public milestone should be `v0.1.0`: a reviewed, reproducible course snapshot with a clean learner route, green CI, compact status pages and one flagship model-to-measurement hardware story.
