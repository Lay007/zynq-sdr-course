# Block 3. DSP Basics

## Purpose
This block introduces FFT, windowing, filtering, and core digital-processing operations required for later modules.

## Why this block matters
Here the student gains the tools required to interpret spectra, suppress interference, and design elementary digital chains.

## Main topics
- FFT and spectrum interpretation;
- window functions and spectral leakage;
- FIR and IIR filters;
- convolution and system response;
- decimation and interpolation;
- numerical tradeoffs in DSP implementation.

## Practical work
- comparing windows by sidelobes and resolution;
- designing simple filters;
- analyzing filter impact on an IQ recording;
- building a small multirate processing chain.

## Tooling for the block
The main toolset is: MATLAB, Python, Simulink, GNU Radio.

## Expected outputs
- spectra before and after processing;
- filter parameters;
- window comparison table;
- report on DSP tradeoffs.

## Folder structure
```text
block_03_dsp_basics/
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
1. study FFT and windows.
2. design basic filters.
3. validate multirate operations in models and scripts.
4. document the processing-method comparison.

## Next step
After finishing this block, the student should be ready to reuse its results as the starting point for the next stage of the course and the related practical experiment.
