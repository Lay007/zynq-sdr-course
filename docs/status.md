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
| 05 | FPGA / HDL flow | Measured signoff candidate | The canonical suite now includes 36 HDL tests. The payload-telemetry image is fully routed at WNS +0.009 ns / WHS +0.028 ns, clean-boots on board B and produces a live preamble/payload split; the shipped differential-QPSK image (the current board-B modem) closes at WNS +0.036 ns. | Demonstrate repeat-build/seed timing robustness of the routed image. |
| 06 | RF frontend and AD9363 | Measured | RX-only, OTA tone, protected conducted-tone baseline, first relative gain table, and a measured 30 dB attenuator flat from 50 MHz to 1 GHz | Measure cable loss separately, repeat the table across frequency and establish a connector-to-connector large-signal limit. |
| 07 | TX/RX chains | Executable | DUC/DDC demos and loopback models | Add measurement package. |
| 08 | Modulation and synchronization | Executable + RTL baseline | CFO/timing, QPSK, 16-QAM, GFSK, DSSS, OFDM and packet CSS models plus a bit-exact SF7 dechirp/sequential-detector RTL regression over all symbols | The compact detector is educational; SF5–SF12 LoRa PHY, interoperability, oversampled correlation, packet/ToA logic and board integration remain in [zynq-lora-phy-positioning](https://github.com/Lay007/zynq-lora-phy-positioning). |
| 09 | Recording and analysis tools | Measured | CI16/CU8/CF32/WAV readers, fail-closed manifest CI, a public 64 KiB synthetic QPSK Git LFS fixture with zero-BER replay, and measured QPSK multi-burst BER/EVM/CFO analysis | Complete publication review or external archival for the separate measured raw QPSK WAV. |
| 10 | KiCad and basic electronics | Draft | Calculators and templates | Add measured breadboard photos and KiCad exports. |
| 11 | Integrated SDR project | Portfolio-ready (two-board link complete) | The in-fabric QPSK modem is closed on a two-board 915 MHz RF link. Bit 189 was traced to the RX DC blocker tracking the modulation (fixed with a running-average estimator, Lab 11.41); the residual ~1% whole-burst rotation floor to a frame-sync false lock (LOCK_ERR_TOL 3→1, Lab 11.42) and then to the four-branch resolution itself (removed by differential QPSK + a 24-symbol preamble, Lab 11.43–11.45). Result: gross whole-burst rotation 0, payload BER ~4×10⁻⁴, rotation-invariant; fabric loopback BER < 5.34×10⁻⁷ over 5.6 M bits. Lab 11.4 is the final measurement report. | Chase the residual differential single-bit rate only if an application needs it — it is the inherent ~3 dB differential penalty, not a rotation failure. |
| 12 | Final projects | Ready framework + reference implementation | Final-project framework: briefs 12.1–12.4 (QPSK modem, RF capture, FPGA DSP block, full SDR report), per-tool READMEs, report templates and grading rubric. Project 12.1 (QPSK modem) is anchored by the completed Block 11 two-board modem as a worked reference exemplar (Lab 11.4). | Learners pick a track and produce their own proposal, verification set and report. |

## Hardware validation priorities

| Priority | Task | Done when |
|---|---|---|
| P0 | Safe cabled loopback | Attenuation, gain settings, capture metadata and short conclusion are recorded. |
| P0 | Runtime PL BPSK/QPSK robustness | Success count / total attempts is repeatable from clean boot and reported with limitations. |
| P1 | QPSK demo dataset | ✔ Public Git LFS payload, manifest, checksum, deterministic rebuild, constellation, BER/SER, EVM/SNR and replay command exist. |
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

The `v0.1.0` release candidate is content-complete: it has a clean learner route, green CI, compact status pages and one flagship model-to-measurement hardware story. The remaining release action is to verify the final commit, create the annotated tag and publish the GitHub Release. The synthetic QPSK replay package is publication-ready; publication review of the separate measured OTA WAV remains open.
