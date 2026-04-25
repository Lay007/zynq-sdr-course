# Block 7. Transmit and Receive Chains

## Purpose
This block focuses on TX/RX chain construction, digital frequency translation, DUC/DDC, and matching data formats between stages.

## Why this block matters
It shows how separate DSP operations become a coherent transmit/receive chain suitable for hardware implementation.

## Main topics
- transmit-chain structure;
- receive-chain structure;
- DUC and DDC;
- numeric formats and interfaces between blocks;
- loopback and chain validation;
- basic chain-validation scenarios.

## Practical work
- building a simple TX/RX model chain;
- analyzing frequency translation in DUC/DDC;
- comparing loopback and external reception;
- preparing a signal-interface map.

## Tooling for the block
The main toolset is: Simulink, MATLAB, Python, GNU Radio.

## Expected outputs
- chain block diagram;
- interface and sampling-rate table;
- loopback-validation results;
- chain-structure report.

## Folder structure
```text
block-7/
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
1. describe TX and RX architecture.
2. implement DUC/DDC in models.
3. connect the chain to loopback or external observation.
4. document the signal interfaces.

## Next step
After finishing this block, the student should be ready to reuse its results as the starting point for the next stage of the course and the related practical experiment.
