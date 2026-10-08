# 02. Preparing the Software Environment

## Purpose of the section
To prepare the software environment for the first block of the course and understand the role of each tool.

## 1. General approach
Several software tools are used in the course. They are needed not “for quantity”, but because each one solves a specific engineering task:

- **Python** — the course's reference language: every lab script, figure and metric is produced by it;
- **RTL-SDR** — an inexpensive external receiver for the first experiments;
- **spectrum viewer** (HDSDR, SDR#, SDR++ or GQRX) — fast observation of spectrum and waterfall;
- **MATLAB / Simulink** — an optional parallel route for modeling and fixed-point preparation;
- **C/C++** — high-performance utilities and signal-processing tools;
- **GNU Radio** — visual assembly of SDR chains;
- **Icarus Verilog** — simulation of the course RTL from Block 5 on;
- **Vivado / Vitis** — the route toward implementation on the Xilinx platform;
- **KiCad** — reading schematics and preparing the hardware side of the course;
- **VS Code** — the main working environment of the project.

## 2. Minimum software set to get started
For the first laboratory work it is enough to install:

1. **Python 3** and the course dependencies;
2. **RTL-SDR driver**;
3. **a spectrum viewer** (HDSDR or SDR# on Windows, SDR++ on any system, GQRX on Linux);
4. **VS Code** (or any editor).

This already allows the student to:

- receive a signal;
- observe the spectrum;
- record data;
- perform basic analysis.

MATLAB and Simulink are not required: every lab of the course runs in Python, and the MATLAB pages are a parallel route for students who have a licence.

## 3. Extended software set
For later stages of the course it is recommended to install:

- **Icarus Verilog** (Block 5 and later);
- **GNU Radio**;
- **Vivado / Vitis** (only for synthesis and the board);
- **KiCad**;
- **C/C++ toolchain**;
- **MATLAB / Simulink** with Fixed-Point Designer and HDL Coder, if available.

## 4. Installing the course Python environment
### Purpose
The course scripts read IQ files, generate figures and write the metrics that the lab pages quote. Everything a lab needs is pinned in `requirements.txt`.

### What needs to be done
```bash
git clone https://github.com/Lay007/zynq-sdr-course.git
cd zynq-sdr-course
python tools/tasks.py install
python tools/tasks.py labs
```

`install` installs the pinned packages (`numpy`, `matplotlib` and the documentation tools); `labs` runs the representative lab scripts. If `labs` finishes without errors, the Python part of the environment is ready.

### Example tasks in Block 1
- load a recording of complex samples;
- compute FFT;
- find the frequency of the maximum peak;
- visualize the spectrum.

## 5. Installing RTL-SDR
### Purpose
RTL-SDR is used as a simple external receiver for observing the signal produced by the training SDR board.

### What needs to be done
- connect RTL-SDR to the computer;
- install the device driver:
  - **Windows:** run Zadig, choose the device's **interface 0** (Bulk-In) and install **WinUSB** (Lab 1.0 shows the screens);
  - **Linux:** install the `rtl-sdr` package and keep the kernel DVB-T driver away from the stick (`blacklist dvb_usb_rtl28xxu` in `/etc/modprobe.d/`);
- verify that the system recognizes the device (`rtl_test` prints the tuner type);
- check that the receiver is available in the spectrum viewer.

### Important notes
- it is preferable to use a USB port without an overloaded hub;
- when working near a transmitter, be careful with signal levels;
- for direct cable connection, use attenuation if necessary.

## 6. Installing a spectrum viewer
### Purpose
A spectrum viewer is used for observing:

- the spectrum;
- the waterfall;
- the signal frequency;
- the signal level;
- signal behavior over time.

HDSDR and SDR# are Windows programs; SDR++ runs on Windows, Linux and macOS; GQRX is common on Linux. The course pages use HDSDR in their examples, but any of them does the job.

### What to check after installation
- the program starts correctly;
- RTL-SDR is selected as the signal source;
- the spectrum reacts when tuning frequency changes;
- the noise floor and received signals are visible;
- the program can record **baseband IQ**, not only demodulated audio.

## 7. MATLAB and Simulink (optional)
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
- comparing results with the spectrum viewer and Python;
- forming an intuitive understanding of the chain.

## 10. Installing Vivado / Vitis
### Purpose
Vivado / Vitis is used for work with the Xilinx platform:

- project build;
- hardware configuration;
- interaction with SoC;
- preparation of the route from model to hardware.

### In the first block
These tools may be considered only at an overview level, without deep use. Vivado is a large download; the RTL labs of Blocks 5 and 8 run in Icarus Verilog without it.

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
1. Python and `python tools/tasks.py install`
2. RTL-SDR driver
3. Spectrum viewer
4. VS Code

### Next stage
5. Icarus Verilog
6. GNU Radio
7. KiCad
8. C/C++ toolchain
9. MATLAB / Simulink (optional)
10. Vivado / Vitis

## 14. Readiness check
Before the lab, the student should be able to answer “yes” to the following questions:

- Does `python tools/tasks.py labs` finish without errors?
- Is RTL-SDR recognized by the system (`rtl_test` or the spectrum viewer sees it)?
- Does the spectrum viewer start, show the noise floor and record baseband IQ?
- Is VS Code (or another editor) installed?
- Does KiCad launch?

## 15. Minimum checklist before the first lab
- the course repository is cloned and its Python dependencies are installed;
- RTL-SDR is installed and checked;
- a spectrum viewer is installed;
- a place for IQ files and screenshots is prepared.

## 16. Conclusions
The software environment of Block 1 should not be maximally complete, but **sufficient for the first real experiment**.

At this stage it is important not to overload the student, but to provide:

- a working set of tools;
- an understanding of the role of each tool;
- readiness to move on to the hardware part and the first laboratory work.
