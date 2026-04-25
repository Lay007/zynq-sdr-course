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

## Next step
After finishing this block, the student should be ready to reuse its results as the starting point for the next stage of the course and the related practical experiment.
