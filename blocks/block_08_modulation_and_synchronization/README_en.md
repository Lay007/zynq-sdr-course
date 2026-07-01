# Block 8. Modulation and Synchronization

## Purpose
This block introduces digital modulation, demodulation, and core synchronization mechanisms in time, frequency, and phase.

## Why this block matters
It turns SDR from a tone-observation tool into an information-transmission system and links DSP to an actual receiver.

## Main topics
- BPSK, QPSK, and basic constellations;
- pulse shaping;
- symbol timing recovery;
- carrier and phase synchronization;
- decision devices and BER;
- debugging a modulator and a demodulator.

## Practical work
- building a modulator-channel-demodulator chain;
- observing constellations and eye diagrams;
- experiments with frequency and timing mismatch;
- estimating synchronization errors and reception quality.

## Tooling for the block
The main toolset is: MATLAB, Simulink, GNU Radio, Python.

## Expected outputs
- constellations before and after synchronization;
- BER or decision-error plots;
- synchronization-chain description;
- modulation/demodulation report.

## Folder structure
```text
block_08_modulation_and_synchronization/
├── README.md
├── README_ru.md
├── README_en.md
├── CONTENTS_ru.md
├── CONTENTS_en.md
├── assets/
├── images/
├── kicad/
├── simulink/
├── matlab/
├── python/
├── cpp/
├── gnuradio/
└── reports/
```

- `assets/` — reference data and helper materials;
- `images/` — diagrams, screenshots, and photos;
- `kicad/` — schematics and electrical notes;
- `simulink/`, `matlab/`, `python/`, `cpp/`, `gnuradio/` — models and analysis tools;
- `reports/` — reports and report templates.

## Recommended work order
1. assemble a basic digital link.
2. visualize constellations and time diagrams.
3. inject synchronization errors and compensate them.
4. formulate limits and conclusions.

## Real hardware BPSK — spectrum, constellation & SNR/EVM

Real measured BPSK from the course board (Zynq-7020 + AD9361): the same three quantities you
compute in theory — **power spectrum**, **constellation**, and **SNR / EVM** — taken from the
running hardware, comparing the on-chip FPGA receiver in AD9361 **digital loopback** with an
**independent RTL-SDR over the air**.

![Board PL RX — spectrum and constellation (AD9361 digital loopback)](https://lay007.github.io/zynq-sdr-course/assets/hw_bpsk_board_spectrum_constellation.png)

![RTL-SDR — over-the-air BPSK constellation](https://lay007.github.io/zynq-sdr-course/assets/hw_bpsk_rtl_ota_constellation.png)

| Metric | Board PL RX (digital loopback) | RTL-SDR (over the air, ~10 cm) |
|---|---|---|
| EVM | ≈ 1.6 % | ≈ 10.6 % |
| SNR (from EVM) | ≈ 36 dB | ≈ 19.5 dB |
| Carrier frequency offset | 0 (digital, no carrier) | ≈ +2.7 kHz |
| BER | 0 | 0 |

The internal loopback isolates the *modem* — two tight clusters at I = ±1, Q ≈ 0, no carrier.
Over the air the *radio channel* spreads the clusters with noise and rotates them with the
carrier frequency offset (Lab 8.1 / 8.2 seen on real hardware), yet at close range it still
decodes at BER 0. The visual gap between the two constellations *is* the RF channel. Full
walkthrough, numbers and reproduction: **[Lab 8.7 — Real-hardware BPSK metrics](lab_8_7_real_hardware_bpsk_metrics.md)**.

## Next step
After finishing this block, the student should be ready to reuse its results as the starting point for the next stage of the course and the related practical experiment.
