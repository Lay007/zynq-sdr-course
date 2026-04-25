# Block 9. Recording and Analysis Tools

## Purpose
This block systematizes the tools used for capturing, storing, replaying, and analyzing IQ data across several environments.

## Why this block matters
It makes the course reproducible: experiments can be moved between machines, replayed offline, and compared in independent tools.

## Main topics
- IQ file formats and metadata;
- HDSDR for first-look observation;
- GNU Radio flowgraphs for analysis;
- MATLAB and Python as offline tools;
- C++ utilities for processing and conversion;
- data storage, versioning, and reproducibility.

## Practical work
- capturing the same signal in several scenarios;
- comparing spectra across tools;
- preparing metadata for recordings;
- converting and replaying captured data.

## Tooling for the block
The main toolset is: HDSDR, GNU Radio, MATLAB, Python, C++.

## Expected outputs
- set of IQ recordings;
- format and parameter table;
- analysis and conversion scripts;
- toolchain report.

## Folder structure
```text
block_09_recording_and_analysis_tools/
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
1. document the data formats in use.
2. assemble a capture and replay chain.
3. compare analysis results across tools.
4. document data-storage and exchange rules.

## Next step
After finishing this block, the student should be ready to reuse its results as the starting point for the next stage of the course and the related practical experiment.
