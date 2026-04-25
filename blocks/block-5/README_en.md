# Block 5. HDL/FPGA Flow and Xilinx Tools

## Purpose
This block shows how a prepared model turns into HDL, is integrated in Vivado, and is linked with the processor side of the SoC.

## Why this block matters
It connects the algorithmic part of the course with real hardware assembly and turns FPGA work into a practical engineering step.

## Main topics
- HDL-friendly model constraints;
- HDL generation from Simulink;
- testbench and functional verification;
- Vivado block design and IP integration;
- address space, interfaces, and PS control;
- basic build-and-debug cycle.

## Practical work
- preparing a model for HDL Coder;
- inspecting generated HDL structure;
- integrating IP into Vivado;
- matching simulation, synthesis, and hardware behavior.

## Tooling for the block
The main toolset is: Simulink, HDL Coder, Vivado, Vitis.

## Expected outputs
- structural chain diagram;
- interface and register map;
- synthesis results or resource estimates;
- HDL/FPGA flow report.

## Folder structure
```text
block-5/
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
1. prepare an HDL-friendly model.
2. generate and inspect HDL.
3. integrate the IP into Vivado.
4. document the configuration and debug cycle.

## Next step
After finishing this block, the student should be ready to reuse its results as the starting point for the next stage of the course and the related practical experiment.
