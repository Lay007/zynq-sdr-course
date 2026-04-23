# Block 1. Introduction to SDR, Tools, and First Signal Reception

## Description
The first block of the course introduces the hardware and software foundation of the SDR project and leads the student through the first practical lab.

The main idea of the block is to:
- understand what SDR is;
- become familiar with the chain “model → hardware → reception → recording → analysis”;
- prepare the working environment;
- perform the first experiment with a test tone;
- get an initial view of the circuit-design part of the course and the role of KiCad.

This block uses the following concept:

**An SDR board based on Zynq7020 + AD9363 generates a test signal, RTL-SDR receives it, HDSDR displays the spectrum, and the recorded IQ data is analyzed in MATLAB, Simulink, Python, C++, and GNU Radio.**

KiCad is additionally introduced as an engineering tool for reading schematics, documenting electrical connections, and preparing for the later analog and digital hardware labs.

## Block objectives
After completing the block, the student should be able to:

- understand the basic architecture of SDR;
- distinguish the roles of the analog and digital parts of the radio chain;
- navigate the elements of the training setup;
- install and launch the main software tools;
- receive a test signal with RTL-SDR;
- record IQ data;
- perform basic signal analysis;
- understand how a Simulink model is related to implementation on hardware;
- understand why KiCad is part of the course and how it relates to the SDR setup.

## Hardware setup photos

### RTL-SDR V3 Pro

![RTL-SDR V3 Pro](../../docs/images/hardware/rtl_sdr_v3_pro.svg)

The RTL-SDR dongle is used as the external receiver in the first practical lab.

### Xilinx Zynq-7020 + ADRV module

![Xilinx Zynq-7020 with ADRV module — angle 1](../../docs/images/hardware/xilinx_7020_adrv_angle_1.svg)

![Xilinx Zynq-7020 with ADRV module — angle 2](../../docs/images/hardware/xilinx_7020_adrv_angle_2.svg)

These photos show the actual board-level SDR platform used for the hands-on part of Block 1.

## Equipment
The block uses:

- an SDR board based on **Zynq7020 + AD9363**
- an **RTL-SDR** receiver
- a personal computer
- cables, antennas, and adapters
- attenuators and matching elements if required
- a breadboard and basic electronic components for later labs

## Software
Main software set:

- **MATLAB**
- **Simulink**
- **Fixed-Point Designer**
- **HDL Coder** or an equivalent HDL route
- **Vivado / Vitis**
- **HDSDR**
- **RTL-SDR drivers**
- **Python**
- **GNU Radio**
- **C/C++ toolchain**
- **VS Code**
- **KiCad**

Minimum set to get started:
- RTL-SDR driver
- HDSDR
- MATLAB / Simulink
- Python
- VS Code

Recommended in addition:
- GNU Radio
- Vivado / Vitis
- KiCad

## Why KiCad is included
KiCad is introduced as an engineering tool that links software, circuit design, and hardware implementation.

Within Block 1, KiCad is used for:
- viewing and reading schematics of the training setup;
- understanding electrical connections between subsystems;
- preparing for later breadboard-based work;
- getting familiar with schematic entry for simple generators and support circuits.

In later blocks KiCad can be used for:
- designing analog and digital tone generators;
- creating simple helper PCBs;
- generating a bill of materials and design documentation;
- preparing small adapters and support circuits for SDR experiments.

## Topics covered in this block
1. What SDR is
2. Hardware platform of the course
3. Software tools of the course
4. From Simulink model to hardware implementation
5. Introduction to KiCad as a schematic-reading and pre-hardware tool
6. First lab on transmitting and receiving a test tone
7. Recording and analyzing IQ data in several environments

## Core learning chain
This block is built around a complete engineering route:

**Mathematical model → fixed-point representation → sample stream → FPGA/SoC → physical signal → external reception → IQ recording → offline analysis**

Additional engineering line of the course:

**Electrical schematic → breadboard / PCB implementation → connection to the SDR setup → experimental verification**

## First laboratory work
### Title
**Transmission and reception of a test tone**

### Goal
Generate a test tone on the SDR board and receive it with RTL-SDR while visualizing it in HDSDR.

### What the student does
- starts generation of the test signal;
- configures RTL-SDR;
- finds the signal in HDSDR;
- observes the spectrum and waterfall;
- changes signal parameters;
- records an IQ file;
- analyzes the recording using several tools.

## Role of KiCad in Block 1
In the first block KiCad is used in a lightweight format and does not overload the main route.

The student:
- gets familiar with the KiCad interface;
- opens a ready-made schematic of a training node or setup;
- learns to read component symbols and interconnections;
- understands how circuit design is tied to the real experiment.

This becomes the basis for later blocks involving:
- analog generators;
- digital generators based on simple logic ICs;
- simple helper boards and adapters for SDR experiments.

## Practical outcome
After completing the lab, the student obtains:

- the first actually received SDR signal;
- an understanding of how a test tone behaves in the spectrum;
- basic HDSDR observation skills;
- initial experience with recording and analyzing IQ data;
- a first introduction to reading electrical schematics through KiCad.

## Folder structure
```text
block_01_intro_sdr_bilingual/
├── README.md
├── README_ru.md
├── README_en.md
├── CONTENTS_ru.md
├── CONTENTS_en.md
├── 01_theory_intro_ru.md
├── 01_theory_intro_en.md
├── 02_software_setup_ru.md
├── 02_software_setup_en.md
├── 03_hardware_overview_ru.md
├── 03_hardware_overview_en.md
├── 04_model_to_hardware_bridge_ru.md
├── 04_model_to_hardware_bridge_en.md
├── 05_kicad_intro_ru.md
├── 05_kicad_intro_en.md
├── 06_lab1_tone_tx_rx_ru.md
├── 06_lab1_tone_tx_rx_en.md
├── 07_iq_analysis_matlab_ru.md
├── 07_iq_analysis_matlab_en.md
├── 08_iq_analysis_simulink_ru.md
├── 08_iq_analysis_simulink_en.md
├── 09_iq_analysis_python_ru.md
├── 09_iq_analysis_python_en.md
├── 10_iq_analysis_cpp_ru.md
├── 10_iq_analysis_cpp_en.md
├── 11_iq_analysis_gnuradio_ru.md
├── 11_iq_analysis_gnuradio_en.md
├── MEDIA_GUIDE_ru.md
├── MEDIA_GUIDE_en.md
├── images/
├── kicad/
├── simulink/
├── matlab/
├── python/
├── cpp/
└── reports/
```

## Learning outcomes
By the end of the block, the student should:

- understand the basic principles of SDR;
- see the connection between DSP theory, modeling, and real hardware;
- understand the role of circuit design in SDR experiments;
- be able to read very simple training schematics;
- confidently execute the first cycle:
  **generation → transmission → reception → recording → analysis**;
- be prepared for the next blocks, which will introduce:
  - fixed-point processing,
  - HDL implementation,
  - FPGA work,
  - analog and digital support circuits,
  - more complex signals and algorithms.

## Why this block matters
This block is the foundation of the whole course. Its purpose is not only to provide theory but also to shape correct engineering thinking: the same signal must be understandable in the model, on the board, in the receiver, in the recorded file, and in the electrical schematic that supports the experiment.

## Next step
After this block, the student can move on to:
- signal generation in Simulink,
- transition to fixed-point,
- preparation for HDL / FPGA implementation,
- extension of the first lab,
- introduction of circuit-design exercises in KiCad,
- assembling simple analog and digital generators on a breadboard.
