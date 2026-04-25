# Block 4. Simulink and Fixed-Point Preparation

## Purpose
This block moves the student from floating-point models to fixed-point thinking, including word length, overflow, and scaling constraints.

## Why this block matters
It is the bridge between a convenient mathematical model and hardware implementation with limited precision and resources.

## Main topics
- chain modeling in Simulink;
- fixed-point representation and quantization;
- scaling and normalization;
- overflow, saturation, and rounding;
- tracking error versus float model;
- preparing a model for HDL flow.

## Practical work
- comparing float and fixed-point models;
- choosing word lengths at key nodes;
- analyzing overflow and dynamic range;
- preparing a parameterized model for the next block.

## Tooling for the block
The main toolset is: Simulink, Fixed-Point Designer, MATLAB, Python.

## Expected outputs
- data-format table;
- fixed-point error plots;
- scaling settings;
- report on HDL readiness.

## Folder structure
```text
block-4/
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
1. assemble the float model and reference signals.
2. introduce fixed-point constraints.
3. evaluate error and overflow.
4. prepare the model for HDL code generation.

## Next step
After finishing this block, the student should be ready to reuse its results as the starting point for the next stage of the course and the related practical experiment.
