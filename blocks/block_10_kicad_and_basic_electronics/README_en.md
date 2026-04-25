# Block 10. KiCad and Basic Electronics

## Purpose
This block connects the SDR course with electrical schematics, prototyping, and simple analog and digital helper circuits.

## Why this block matters
It removes the artificial separation between DSP and hardware by showing how power, levels, connectors, and support circuitry affect the experiment.

## Main topics
- KiCad interface and project structure;
- reading and releasing schematics;
- power, decoupling, and wiring;
- breadboard work and simple generators;
- connectors, matching, and input protection;
- documentation and BOM preparation.

## Practical work
- opening and reviewing an existing schematic;
- creating a simple helper-circuit schematic;
- preparing a breadboard implementation;
- linking the schematic to a lab experiment.

## Tooling for the block
The main toolset is: KiCad, multimeter, breadboard, MATLAB / Simulink.

## Expected outputs
- schematic or schematic fragment;
- bill of materials;
- photos of the assembly;
- report on the electrical part of the experiment.

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
1. review schematic structure and symbols.
2. assemble a simple helper circuit.
3. verify electrical parameters.
4. connect the schematic to an SDR experiment.

## Next step
After finishing this block, the student should be ready to reuse its results as the starting point for the next stage of the course and the related practical experiment.
