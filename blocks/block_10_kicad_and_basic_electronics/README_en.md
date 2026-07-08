# Block 10. KiCad and Basic Electronics

## Purpose
This block connects the SDR course with electrical schematics, prototyping, simple analog/digital helper circuits and real RF bench measurements.

## Why this block matters
It removes the artificial separation between DSP and hardware by showing how power, levels, connectors, matching, cables, attenuators and filters affect the experiment.

## Main topics
- KiCad interface and project structure;
- reading and releasing schematics;
- power, decoupling, and wiring;
- breadboard work and simple generators;
- connectors, matching, and input protection;
- NanoVNA RF measurements: `S11`, `S21`, VSWR and Smith chart;
- digital attenuator verification for controlled sweeps;
- documentation and BOM preparation.

## Practical work
- opening and reviewing an existing schematic;
- creating a simple helper-circuit schematic;
- preparing a breadboard implementation;
- measuring an RF Demo Kit with a NanoVNA;
- characterizing a digital RF attenuator;
- linking the schematic to an SDR lab experiment.

## Block labs
- Lab 10.1 — Passive RC filter.
- Lab 10.2 — Simple attenuator pad.
- Lab 10.3 — RF measurement safety checklist.
- Lab 10.4 — KiCad schematic mini-project.
- Lab 10.5 — NanoVNA and RF Demo Kit: `S11`/`S21`, VSWR and Smith chart.
- Lab 10.6 — Digital RF attenuator: step, range and linearity check.

## Tooling for the block
The main toolset is: KiCad, multimeter, breadboard, MATLAB / Simulink, NanoVNA, RF Demo Kit, fixed and digital attenuators, 50-ohm cables and loads.

## Expected outputs
- schematic or schematic fragment;
- bill of materials;
- photos of the assembly and measurement bench;
- `S11`/`S21`, VSWR, attenuation and error tables;
- report on the electrical and RF part of the experiment.

## Folder structure
```text
block_10_kicad_and_basic_electronics/
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
1. review schematic structure and symbols;
2. assemble a simple helper circuit;
3. verify electrical parameters;
4. perform NanoVNA calibration and measure the RF Demo Kit;
5. characterize the digital attenuator;
6. connect the results to an SDR experiment with SNR/BER.

## Next step
After finishing this block, the student should be ready to reuse its results for the next course stage: safe RF loopback, controlled attenuation sweeps and explaining differences between the model, FPGA logic and measurement.
