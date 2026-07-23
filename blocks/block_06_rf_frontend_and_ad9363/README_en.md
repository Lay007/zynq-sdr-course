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
- relating AD9363 settings to the observed signal;
- comparing RTL-SDR and AD936x using SNR, SINAD, SFDR, ENOB and clipping;
- requantizing the same AD936x capture to 6/8/10/12 bits to estimate the quantization contribution.

## Lab 6.9

The block now includes **RTL-SDR vs AD936x receiver quality and ADC resolution**:

- [lab description](lab_6_9_receiver_comparison.md);
- [executable analyzer](python/lab_6_9_compare_receivers.py).

The lab separates the complete receiver difference, the effect of reducing one
AD936x capture to lower bit depths, and an approximate same-resolution comparison
after both paths are represented with 8-bit samples. The modulated extension must
check EVM and BER in addition to spectral SNR.

## Tooling for the block
The main toolset is: AD9363 configuration tools, HDSDR, MATLAB, Python, RTL-SDR, NanoVNA and tinySA.

## Expected outputs
- RF chain level map;
- AD9363 settings description;
- screenshots of overload and normal modes;
- RTL-SDR vs AD936x comparison table;
- SINAD and noise-density figures;
- system ENOB and native-to-8-bit penalty estimate;
- RF-stand report.

## Folder structure
```text
block_06_rf_frontend_and_ad9363/
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
1. review the RF-chain structure;
2. document levels and bandwidths;
3. observe overload and noise behavior;
4. calibrate the passive path and complete Lab 6.9;
5. prepare safe-configuration recommendations.

## Next step
After finishing this block, the student should be ready to reuse its results as the starting point for the next stage of the course and the related practical experiment.
