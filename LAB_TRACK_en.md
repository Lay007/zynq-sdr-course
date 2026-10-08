# Learning routes

The course has more than a hundred labs, and not every learner has the same equipment. Pick the route
that matches what you have; each one is a subset of the next, so nothing done on an earlier route is
wasted. The labs run in the order listed.

| Route | You need | What it covers |
|---|---|---|
| A. Laptop only | Python (`python tools/tasks.py install`); Icarus Verilog from step A5 | DSP, sampling, fixed point, modulation and synchronization, RTL simulation, and real recordings that ship with the repository |
| B. + RTL-SDR | an RTL-SDR receiver (about the price of a textbook) and an antenna | your own over-the-air recordings |
| C. + Zynq board | the Zynq-7020 + AD9363 board, cables, attenuators | transmitting, the FPGA receiver on silicon, two-board links |
| D. + bench instruments | NanoVNA, RF attenuators | S-parameters and component measurements |

MATLAB / Simulink are optional throughout: the labs that mention them also run in Python. The one exception is Lab 4.4, which is a Simulink lab; skip it without a licence.

## Route A — laptop only

**A0. Orientation.** Read Block 1: [Introduction to SDR](/zynq-sdr-course/en/block01/01-theory-intro/), [Preparing the Software Environment](/zynq-sdr-course/en/block01/02-software-setup/), [Hardware Platform of the Course](/zynq-sdr-course/en/block01/03-hardware-overview/), [Bridge from Model to Hardware](/zynq-sdr-course/en/block01/04-model-to-hardware-bridge/), [Signal Quality Metrics: FFT, SNR, EVM and BER](/zynq-sdr-course/en/block01/15-signal-metrics/), [FFT and Spectral Analysis](/zynq-sdr-course/en/block01/16-fft-spectral-analysis/), [Link Budget in SDR Systems](/zynq-sdr-course/en/block01/17-link-budget/), [Fixed-Point Effects in DSP and FPGA](/zynq-sdr-course/en/block01/18-fixed-point-effects/).

**A1. Signals, sampling and spectra**

- [Lab 2.1](/zynq-sdr-course/en/labs/lab-2-1-sampling-axis-and-interpretation/) — Sampling Axis and Interpretation
- [Lab 2.2](/zynq-sdr-course/en/labs/lab-2-2-aliasing-sweep/) — Aliasing Sweep
- [Lab 2.3](/zynq-sdr-course/en/labs/lab-2-3-iq-interpretation-and-mirroring/) — I/Q Interpretation and Mirrored Spectrum
- [Lab 3.1](/zynq-sdr-course/en/labs/lab-3-1-fft-windows/) — FFT Windows and Spectral Leakage
- [Lab 3.2](/zynq-sdr-course/en/labs/lab-3-2-fir-low-pass/) — FIR Low-Pass Filtering of IQ Data
- [Lab 3.3](/zynq-sdr-course/en/labs/lab-3-3-digital-mixing/) — Digital Mixing and Frequency Shift
- [Lab 3.4](/zynq-sdr-course/en/labs/lab-3-4-decimation/) — Decimation with Anti-Aliasing Filter
- [Lab 3.5](/zynq-sdr-course/en/labs/lab-3-5-fft-complexity/) — FFT complexity and selected-bin trade-off
- [Lab 3.6](/zynq-sdr-course/en/labs/lab-3-6-convolution-correlation/) — Convolution and correlation for SDR
- [Lab 3.7](/zynq-sdr-course/en/labs/lab-3-7-window-tradeoffs/) — Window trade-offs and weak-signal detection

**A2. Real recordings without hardware.** The repository ships real RTL-SDR and board recordings; these labs read them.

- [Lab 9.1](/zynq-sdr-course/en/labs/lab-9-1-iq-file-format-and-metadata/) — IQ File Format and Metadata
- [Lab 9.2](/zynq-sdr-course/en/labs/lab-9-2-read-ci16-iq-and-analyze/) — Read CI16 IQ and Analyze Spectrum
- [Lab 9.3](/zynq-sdr-course/en/labs/lab-9-3-multi-format-iq-reader/) — Multi-Format IQ Reader
- [Lab 9.4](/zynq-sdr-course/en/labs/lab-9-4-read-wav-iq-and-analyze/) — Read WAV IQ and Analyze Spectrum
- [Lab 9.5](/zynq-sdr-course/en/labs/lab-9-5-synthetic-qpsk-replay-analysis/) — Synthetic QPSK replay and constellation analysis
- [Lab 6.4](/zynq-sdr-course/en/labs/lab-6-4-synthetic-rf-capture-analysis/) — Synthetic RF Capture Analysis
- [Lab 6.7](/zynq-sdr-course/en/labs/lab-6-7-zero-if-artifacts/) — Zero-IF artifacts: DC component, mirror and tune offset

**A3. Fixed point**

- [Lab 4.1](/zynq-sdr-course/en/labs/lab-4-1-fixed-point-fir/) — Fixed-Point FIR Filtering
- [Lab 4.2](/zynq-sdr-course/en/labs/lab-4-2-fixed-point-digital-mixer/) — Fixed-Point Digital Mixer
- [Lab 4.3](/zynq-sdr-course/en/labs/lab-4-3-bpsk-fixed-point-chain/) — BPSK fixed-point chain
- [Lab 4.4](/zynq-sdr-course/en/labs/lab-4-4-bpsk-simulink-and-ber/) — BPSK Simulink chain and ideal BER vs SNR

**A4. TX/RX chains, modulation and synchronization**

- [Lab 7.1](/zynq-sdr-course/en/labs/lab-7-1-tx-rx-chain-architecture/) — TX/RX Chain Architecture
- [Lab 7.2](/zynq-sdr-course/en/labs/lab-7-2-duc-ddc-frequency-translation/) — DUC/DDC Frequency Translation
- [Lab 7.3](/zynq-sdr-course/en/labs/lab-7-3-tx-rx-loopback-metrics/) — TX/RX Loopback Metrics
- [Lab 7.4](/zynq-sdr-course/en/labs/lab-7-4-packet-receiver-detection/) — Packet receiver chain and frame detection
- [Lab 7.5](/zynq-sdr-course/en/labs/lab-7-5-cic-decimator/) — CIC decimator for SDR receiver chains
- [Lab 8.1](/zynq-sdr-course/en/labs/lab-8-1-cfo-estimation-correction/) — Carrier Frequency Offset Estimation and Correction
- [Lab 8.2](/zynq-sdr-course/en/labs/lab-8-2-phase-offset-correction/) — Phase Offset Estimation and Decision-Directed Correction
- [Lab 8.3](/zynq-sdr-course/en/labs/lab-8-3-timing-recovery/) — Symbol Timing Offset and Recovery
- [Lab 8.4](/zynq-sdr-course/en/labs/lab-8-4-end-to-end-sync-chain/) — End-to-End Synchronization Chain
- [Lab 8.5](/zynq-sdr-course/en/labs/lab-8-5-ofdm-mini-link/) — OFDM mini link (CP, pilots, sync, equalization)
- [Lab 8.6](/zynq-sdr-course/en/labs/lab-8-6-channel-coding-ber-comparison/) — Channel coding BER comparison with interleaving
- [Lab 8.7](/zynq-sdr-course/en/labs/lab-8-7-snr-vs-ber-traps/) — SNR is not enough: BER/EVM traps
- [Lab 8.8](/zynq-sdr-course/en/labs/lab-8-8-qpsk-modem-impairments/) — QPSK modem, impairments and BER
- [Lab 8.9](/zynq-sdr-course/en/labs/lab-8-9-qpsk-carrier-recovery/) — QPSK carrier recovery (decision-directed Costas loop)
- [Lab 8.10](/zynq-sdr-course/en/labs/lab-8-10-ofdm-papr-clipping/) — OFDM PAPR, clipping and spectral regrowth
- [Lab 8.11](/zynq-sdr-course/en/labs/lab-8-11-16qam-tradeoffs/) — 16-QAM bridge: BER, EVM and implementation limits
- [Lab 8.12](/zynq-sdr-course/en/labs/lab-8-12-gfsk-bt-ber/) — GFSK: BT, occupied bandwidth and discriminator BER
- [Lab 8.13](/zynq-sdr-course/en/labs/lab-8-13-dsss-processing-gain/) — DSSS acquisition and processing gain
- [Lab 8.20](/zynq-sdr-course/en/labs/lab-8-20-css-waveform/) — CSS chirp waveform and symbol mapping
- [Lab 8.21](/zynq-sdr-course/en/labs/lab-8-21-css-dechirp-fft/) — CSS dechirp and FFT detector
- [Lab 8.22](/zynq-sdr-course/en/labs/lab-8-22-css-packet-sync-per/) — Packet-level CSS synchronization and PER
- [Lab 6.2](/zynq-sdr-course/en/labs/lab-6-2-gain-staging-and-overload/) — Gain Staging and Overload
- [Lab 6.5](/zynq-sdr-course/en/labs/lab-6-5-rf-impairment-calibration/) — RF impairment calibration (DC, IQ imbalance, LO leakage)

**A5. RTL simulation** (install Icarus Verilog; Vivado is not needed)

- [Lab 5.1](/zynq-sdr-course/en/labs/lab-5-1-streaming-interface-and-testbench/) — Streaming DSP Interface and Testbench
- [Lab 5.2](/zynq-sdr-course/en/labs/lab-5-2-fir-rtl-mapping/) — FIR RTL Mapping
- [Lab 5.3](/zynq-sdr-course/en/labs/lab-5-3-nco-mixer-rtl/) — Fixed-Point NCO Mixer RTL
- [Lab 5.4](/zynq-sdr-course/en/labs/lab-5-4-axis-wrapper/) — AXI-Stream Wrapper
- [Lab 5.5](/zynq-sdr-course/en/labs/lab-5-5-float-fixed-rtl-comparison/) — Float vs fixed-point vs RTL comparison
- [Lab 5.6](/zynq-sdr-course/en/labs/lab-5-6-bpsk-rrc-tx-fir-rtl/) — BPSK RRC TX FIR RTL
- [Lab 5.7](/zynq-sdr-course/en/labs/lab-5-7-bpsk-upsampler-8x/) — BPSK 8x symbol upsampler
- [Lab 5.8](/zynq-sdr-course/en/labs/lab-5-8-bpsk-rx-bit-recovery/) — BPSK RX matched filter and bit recovery
- [Lab 5.9](/zynq-sdr-course/en/labs/lab-5-9-bpsk-framed-loopback/) — BPSK framed TX/RX loopback top-level
- [Lab 5.10](/zynq-sdr-course/en/labs/lab-5-10-bpsk-zynq-ready-top/) — Zynq-ready BPSK BER top-level
- [Lab 8.14](/zynq-sdr-course/en/labs/lab-8-14-ofdm-rtl-chain/) — OFDM RTL: mapper to equalized loopback

**A6. System design and reports**

- [Lab 10.1](/zynq-sdr-course/en/labs/lab-10-1-rc-filter/) — Passive RC Filter
- [Lab 10.2](/zynq-sdr-course/en/labs/lab-10-2-attenuator-pad/) — Simple Attenuator Pad
- [Lab 10.3](/zynq-sdr-course/en/labs/lab-10-3-rf-measurement-safety-checklist/) — RF Measurement Safety Checklist
- [Lab 10.4](/zynq-sdr-course/en/labs/lab-10-4-kicad-schematic-mini-project/) — KiCad Schematic Mini-Project
- [Lab 11.1](/zynq-sdr-course/en/labs/lab-11-1-project-requirements-and-architecture/) — Project Requirements and System Architecture
- [Lab 11.2](/zynq-sdr-course/en/labs/lab-11-2-end-to-end-simulation-package/) — End-to-End Simulation Package
- [Lab 11.3](/zynq-sdr-course/en/labs/lab-11-3-fpga-rf-integration-checklist/) — FPGA/RF Integration Checklist
- [Lab 11.4](/zynq-sdr-course/en/labs/lab-11-4-final-measurement-report/) — Final Measurement Report
- [Lab 11.5](/zynq-sdr-course/en/labs/lab-11-5-axi-dma-latency-jitter/) — AXI DMA pipeline latency and jitter
- [Lab 11.6](/zynq-sdr-course/en/labs/lab-11-6-measurement-uncertainty-budget/) — Measurement uncertainty budget and reporting
- [Project 12.1](/zynq-sdr-course/en/labs/project-12-1-qpsk-modem-final-project/) — QPSK Modem Final Project
- [Project 12.3](/zynq-sdr-course/en/labs/project-12-3-fpga-dsp-block-final-project/) — FPGA DSP Block Final Project

## Route B — add an RTL-SDR

Everything on route A, plus:

- [Lab 1.0](/zynq-sdr-course/en/labs/lab-1-0-first-rtl-sdr-observation/) — First RF Observation with RTL-SDR
- [Lab 6.1](/zynq-sdr-course/en/labs/lab-6-1-frequency-plan/) — RF Frequency Plan
- [Project 12.2](/zynq-sdr-course/en/labs/project-12-2-rf-capture-analysis-final-project/) — RF Capture Analysis Final Project

Record your own WAV in Lab 1.0 and analyse it with the scripts of Labs 9.4 and 6.4 instead of the shipped recordings.

## Route C — add the Zynq board

Everything on routes A and B, plus the board itself:

- [Lab 1.1](/zynq-sdr-course/en/labs/lab-1-1-controlled-zynq-tone-rtl-sdr/) — Controlled Zynq DDS Tone with RTL-SDR
- [Lab 6.3](/zynq-sdr-course/en/labs/lab-6-3-ad9363-settings-iio-attr/) — AD9363 Settings and iio_attr Quick Reference
- [Lab 6.6](/zynq-sdr-course/en/labs/lab-6-6-zynq-rx-only-observation/) — Zynq RX-only observation on the clean image
- [Lab 6.8](/zynq-sdr-course/en/labs/lab-6-8-zynq-ota-tone-observation/) — Zynq stock-shell OTA DDS tone observation
- [Lab 6.9](/zynq-sdr-course/en/labs/lab-6-9-receiver-comparison/) — RTL-SDR vs AD936x receiver quality and ADC resolution
- [Lab 6.10](/zynq-sdr-course/en/labs/lab-6-10-agc-phase-transition/) — AGC/LNA Gain-Transition Phase-Discontinuity Analysis
- [Lab 6.11](/zynq-sdr-course/en/labs/lab-6-11-tx-power-calibration/) — dBm vs dBFS power calibration
- [Lab 5.11](/zynq-sdr-course/en/labs/lab-5-11-bpsk-axi-lite-control/) — AXI-Lite control wrapper for the BPSK BER top-level
- [Lab 5.12](/zynq-sdr-course/en/labs/lab-5-12-zynq-ps-pl-mailbox/) — PS↔PL message mailbox: the first meaningful Zynq bridge
- [Lab 8.15](/zynq-sdr-course/en/labs/lab-8-15-real-hardware-bpsk-metrics/) — Real-hardware BPSK: spectrum, constellation and SNR/EVM

Then the integrated project of Block 11, the core path from a PS-controlled modem to a two-board link:

- [Lab 11.7](/zynq-sdr-course/en/labs/lab-11-7-axi-lite-bpsk-bringup/) — PS-side AXI-Lite BPSK bring-up
- [Lab 11.14](/zynq-sdr-course/en/labs/lab-11-14-stock-shell-bpsk-ota/) — Stock-shell host BPSK OTA fallback
- [Lab 11.27](/zynq-sdr-course/en/labs/lab-11-27-runtime-qpsk-digital-loopback/) — Runtime QPSK digital-loopback BER
- [Lab 11.28](/zynq-sdr-course/en/labs/lab-11-28-rtl-sdr-ota-qpsk/) — Runtime QPSK through an external RTL-SDR
- [Lab 11.29](/zynq-sdr-course/en/labs/lab-11-29-cold-boot-ber-campaign/) — Cold-boot BER reliability campaign
- [Lab 11.30](/zynq-sdr-course/en/labs/lab-11-30-two-board-cfo-validation/) — Coarse-CFO estimator on a real two-board link
- [Lab 11.31](/zynq-sdr-course/en/labs/lab-11-31-coarse-cfo-stress-sweep/) — Coarse-CFO estimator stress sweep
- [Lab 11.32](/zynq-sdr-course/en/labs/lab-11-32-two-board-fabric-coarse-cfo/) — Two-board coarse-CFO acquisition in the FPGA fabric
- [Lab 11.34](/zynq-sdr-course/en/labs/lab-11-34-continuous-qpsk-timing-recovery/) — Continuous QPSK Gardner timing recovery
- [Lab 11.38](/zynq-sdr-course/en/labs/lab-11-38-hardware-tx-iq-capture-offline-rx/) — ZynqSDR TX → IQ capture → offline receiver
- [Lab 11.45](/zynq-sdr-course/en/labs/lab-11-45-differential-long-preamble/) — Differential QPSK + a longer preamble: the rotation floor, gone
- [Lab 11.46](/zynq-sdr-course/en/labs/lab-11-46-two-board-console-message/) — A message from one Zynq console to another
- [Project 12.4](/zynq-sdr-course/en/labs/project-12-4-full-sdr-measurement-report/) — Full SDR Measurement Report

The other Block 11 labs (11.8–11.26, 11.33, 11.35, 11.41, 11.42) are the bring-up history of that path: each records one failure, how it was found and how it was fixed. Read them as case studies once the core path is clear.

## Route D — add bench instruments

- [Lab 10.5](/zynq-sdr-course/en/labs/lab-10-5-nanovna-rf-demo-kit/) — NanoVNA and RF Demo Kit: S11/S21, VSWR and Smith Chart
- [Lab 10.6](/zynq-sdr-course/en/labs/lab-10-6-digital-attenuator-characterization/) — Digital RF Attenuator: Step, Range and Linearity Check

## What each block assumes

| Block | Comes after | New tools |
|---|---|---|
| 1. Introduction | — | Python, a spectrum viewer |
| 2. Signals and sampling | Block 1 | — |
| 3. DSP basics | Block 2 | — |
| 4. Fixed point | Block 3 | (MATLAB / Simulink optional) |
| 5. FPGA / HDL | Blocks 3–4 | Icarus Verilog; Vivado only for synthesis |
| 6. RF frontend | Blocks 2–3 | RTL-SDR or the board for the live parts |
| 7. TX/RX chains | Blocks 3, 6 | — |
| 8. Modulation and synchronization | Block 7 | Icarus Verilog for 8.14 |
| 9. Recording and analysis | Block 2 | — |
| 10. Electronics and KiCad | Block 1 | KiCad; NanoVNA for 10.5–10.6 |
| 11. Integrated project | Blocks 5–8 | the board |
| 12. Final projects | the route you followed | — |

## Report format
Every lab report contains the goal, the equipment, the parameters, the procedure, the plots or screenshots and an engineering conclusion with numbers. See the [lab report template](/zynq-sdr-course/lab-report-template/).
