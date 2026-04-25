# 02. Preparing the Software Environment

## Purpose of the section
To prepare the software environment for the first block of the course and understand the role of each tool.

## 1. General approach
Several software tools are used in the course. They are needed not “for quantity”, but because each one solves a specific engineering task:

- **HDSDR** — fast observation of spectrum and waterfall;
- **RTL-SDR** — an inexpensive external receiver for the first experiments;
- **MATLAB / Simulink** — modeling, analysis, and algorithm preparation;
- **Python** — offline analysis and quick automation;
- **C/C++** — high-performance utilities and signal-processing tools;
- **GNU Radio** — visual assembly of SDR chains;
- **Vivado / Vitis** — the route toward implementation on the Xilinx platform;
- **KiCad** — reading schematics and preparing the hardware side of the course;
- **VS Code** — the main working environment of the project.

## 2. Minimum software set to get started
For the first laboratory work it is enough to install:

1. **RTL-SDR driver**
2. **HDSDR**
3. **MATLAB / Simulink**
4. **Python**
5. **VS Code**

This already allows the student to:
- receive a signal;
- observe the spectrum;
- record data;
- perform basic analysis.

## 3. Extended software set
For later stages of the course it is recommended to install:

- **GNU Radio**
- **Vivado / Vitis**
- **KiCad**
- **C/C++ toolchain**
- additional DSP libraries if needed

## 4. Installing RTL-SDR
### Purpose
RTL-SDR is used as a simple external receiver for observing the signal produced by the training SDR board.

### What needs to be done
- connect RTL-SDR to the computer;
- install the device driver;
- verify that the system recognizes the device;
- check that the receiver is available in the SDR software.

### Important notes
- it is preferable to use a USB port without an overloaded hub;
- when working near a transmitter, be careful with signal levels;
- for direct cable connection, use attenuation if necessary.

## 5. Installing HDSDR
### Purpose
HDSDR is used for observing:
- the spectrum;
- the waterfall;
- the signal frequency;
- the signal level;
- signal behavior over time.

### What to check after installation
- the program starts correctly;
- RTL-SDR is selected as the signal source;
- the spectrum reacts when tuning frequency changes;
- the noise floor and received signals are visible.

## 6. Installing MATLAB and Simulink
### Purpose
MATLAB and Simulink are used for:
- signal modeling;
- building test chains;
- spectral analysis;
- preparation for fixed-point;
- later transition to hardware implementation.

### In the first block they are needed for
- analysis of the recorded IQ file;
- FFT calculation;
- estimating tone frequency and level;
- connecting the model to future hardware implementation.

### Recommended components
- Simulink
- DSP-related toolboxes
- Fixed-Point Designer
- HDL Coder

## 7. Installing Python
### Purpose
Python is needed as a fast universal tool for:
- reading IQ files;
- plotting spectra;
- automatic analysis;
- creating small utilities.

### Recommended libraries
- `numpy`
- `scipy`
- `matplotlib`

### Example tasks in Block 1
- load a recording of complex samples;
- compute FFT;
- find the frequency of the maximum peak;
- visualize the spectrum.

## 8. Installing a C/C++ toolchain
### Purpose
C/C++ is needed for:
- creating fast utilities;
- offline processing of large files;
- preparing real DSP tools;
- later integration into real-time projects.

### In the first block
C/C++ is used in a lightweight way:
- reading IQ files;
- simple spectral analysis;
- creating a student’s own processing utility.

## 9. Installing GNU Radio
### Purpose
GNU Radio allows the student to quickly build an SDR chain from ready-made blocks and visually debug signal flow.

### In the first block
GNU Radio can be used for:
- reading a recorded file;
- displaying the spectrum;
- comparing results with HDSDR and MATLAB;
- forming an intuitive understanding of the chain.

## 10. Installing Vivado / Vitis
### Purpose
Vivado / Vitis is used for work with the Xilinx platform:
- project build;
- hardware configuration;
- interaction with SoC;
- preparation of the route from model to hardware.

### In the first block
These tools may be considered only at an overview level, without deep use.

The main goal is:
- to understand that hardware implementation does not appear “by itself”;
- to see the place of Xilinx tools in the overall learning route.

## 11. Installing KiCad
### Purpose
KiCad is used as an engineering tool for:
- reading schematics;
- preparing circuit-design labs;
- creating simple helper boards;
- understanding the electrical connections of the training setup.

### In the first block
KiCad is mainly needed for:
- getting familiar with the interface;
- opening ready-made schematics;
- reading power, signal lines, and connectors.

## 12. Installing VS Code
### Purpose
VS Code acts as the main working environment of the project.

It is convenient for:
- editing Markdown;
- running Python scripts;
- working with C/C++;
- maintaining the course repository;
- preparing lab materials.

## 13. Recommended installation order
### Minimum start
1. RTL-SDR driver
2. HDSDR
3. MATLAB / Simulink
4. Python
5. VS Code

### Next stage
6. GNU Radio
7. KiCad
8. C/C++ toolchain
9. Vivado / Vitis

## 14. Readiness check
Before the lab, the student should be able to answer “yes” to the following questions:

- Is RTL-SDR recognized by the system?
- Does HDSDR start and see the signal source?
- Does MATLAB start?
- Does Simulink open?
- Does Python work from the console?
- Is VS Code installed?
- Does KiCad launch?

## 15. Minimum checklist before the first lab
- RTL-SDR is installed and checked;
- HDSDR is installed;
- MATLAB / Simulink is prepared;
- Python is installed;
- the project folder is prepared;
- the block directory structure is created;
- a place for IQ files and screenshots is prepared.

## 16. Conclusions
The software environment of Block 1 should not be maximally complete, but **sufficient for the first real experiment**.

At this stage it is important not to overload the student, but to provide:
- a working set of tools;
- an understanding of the role of each tool;
- readiness to move on to the hardware part and the first laboratory work.
