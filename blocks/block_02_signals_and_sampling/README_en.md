# Block 2. Signals, Spectrum, Sampling, and I/Q

## Purpose
This block builds a solid understanding of continuous and discrete signals, spectrum, aliasing, and complex I/Q representation.

## Why this block matters
Without it, the student cannot confidently read spectra, choose sampling rates, or understand artifacts in SDR data.

## Main topics
- continuous and discrete signals;
- frequency-domain view and bandwidth;
- sampling rate and aliasing;
- complex envelope and I/Q;
- relation between tone, spectrum, and recorded data;
- basic parameter-selection mistakes.

## Practical work
- comparing spectra at different sampling rates;
- visualizing aliasing in models and scripts;
- building I/Q trajectories and basic spectra;
- matching a model with a recorded signal.

## Tooling for the block
The main toolset is: MATLAB, Simulink, Python, GNU Radio.

## Expected outputs
- time-domain and spectrum plots;
- sampling-parameter table;
- comparison of aliasing scenarios;
- block laboratory report.

## Folder structure
```text
block_02_signals_and_sampling/
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
1. review sampling and spectrum theory.
2. assemble models and scripts for experiments.
3. run a set of sampling-rate comparisons.
4. document conclusions about I/Q and aliasing.

## Next step
After finishing this block, the student should be ready to reuse its results as the starting point for the next stage of the course and the related practical experiment.
