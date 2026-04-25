# Block 11. Integrated SDR Project

## Purpose
This block combines the previously studied elements into one system: model, DSP chain, hardware platform, analysis tools, and documentation.

## Why this block matters
Here the student learns system-level integration rather than isolated operations, with all subsystems required to work together.

## Main topics
- integrated-project decomposition;
- signal and interface architecture;
- combining DSP, RF, and control logic;
- verification and test plan;
- project repository and documentation structure;
- system readiness criteria.

## Practical work
- assembling an end-to-end chain;
- documenting interfaces between modules;
- preparing verification scenarios;
- running integration tests.

## Tooling for the block
The main toolset is: Simulink, Vivado, MATLAB, Python, KiCad.

## Expected outputs
- project architecture diagram;
- interface table;
- integration-test protocol;
- integrated report.

## Folder structure
```text
block_11_integrated_sdr_project/
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
1. split the project into subsystems.
2. align interfaces and data formats.
3. run integration tests.
4. prepare system documentation.

## Next step
After finishing this block, the student should be ready to reuse its results as the starting point for the next stage of the course and the related practical experiment.
