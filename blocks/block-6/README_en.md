# Block 6. RF Frontend and AD9363

## Purpose
This block studies the real RF chain, signal levels, gain distribution, bandwidth, and the specifics of the AD9363 transceiver.

## Why this block matters
Without understanding the RF portion, the student cannot explain overload, noise, or proper receiver and transmitter settings.

## Main topics
- RX and TX chain structure;
- levels, gain staging, and dynamic range;
- LO frequencies, bandwidth, and filters;
- AD9363 operating modes;
- noise, overload, and intermodulation;
- engineering discipline in RF connections.

## Practical work
- building a level table across the chain;
- experiments with gain and bandwidth;
- analyzing overload signatures in the spectrum;
- relating AD9363 settings to the observed signal.

## Tooling for the block
The main toolset is: AD9363 configuration tools, HDSDR, MATLAB, Python.

## Expected outputs
- RF chain level map;
- AD9363 settings description;
- screenshots of overload and normal modes;
- RF-stand report.

## Folder structure
```text
block-6/
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
1. review the RF-chain structure.
2. document levels and bandwidths.
3. observe overload and noise behavior.
4. prepare safe-configuration recommendations.

## Next step
After finishing this block, the student should be ready to reuse its results as the starting point for the next stage of the course and the related practical experiment.
