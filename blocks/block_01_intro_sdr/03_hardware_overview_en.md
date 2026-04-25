# 03. Hardware Platform of the Course

## Purpose of the section
To become familiar with the training SDR setup, understand the role of each device, and prepare for safe execution of the first laboratory work.

## 1. Components of the training setup
The first block uses:
- an SDR board based on **Zynq7020 + AD9363**
- an external **RTL-SDR** receiver
- a personal computer
- interconnection cables
- antennas or a cable link
- attenuators and adapters when required

### Hardware photos

#### RTL-SDR V3 Pro

![RTL-SDR V3 Pro](../../images/hardware/rtl_sdr_v3_pro.svg)

#### Xilinx Zynq-7020 + ADRV module

![Xilinx Zynq-7020 with ADRV module](../../images/hardware/xilinx_7020_adrv_angle_1.svg)

This image shows the actual board-level SDR platform used in the first practical SDR experiments of the course.

### SDR stand flow

| Step | Block | Role | Output |
|---:|---|---|---|
| 1 | **Model & Control** | Simulink / HDL / software setup | Parameters and generated samples |
| ↓ |  | **configure / generate** |  |
| 2 | **Zynq-7020 + ADRV** | FPGA / SoC processing and RF TX/RX path | RF signal |
| ↓ |  | **RF over air or cable** |  |
| 3 | **RTL-SDR** | External receiver for first signal capture | Received sample stream |
| ↓ |  | **observe** |  |
| 4 | **HDSDR** | Spectrum and waterfall visualization | Visible signal and tuned recording setup |
| ↓ |  | **store** |  |
| 5 | **IQ Recording** | Captured IQ sample file | IQ dataset |
| ↓ |  | **analyze** |  |
| 6 | **Offline Analysis** | MATLAB / Simulink / Python / C++ / GNU Radio | Plots, metrics, reports, conclusions |

**Practical flow:** generate a signal on the Zynq/ADRV platform → receive it with RTL-SDR → observe it in HDSDR → record IQ samples → analyze the recording in multiple software environments.

In later stages the course will also use:
- a solderless breadboard;
- basic analog components;
- basic digital ICs;
- helper boards and adapters.

## 2. SDR board based on Zynq7020 + AD9363
### Purpose
This is the main training hardware platform of the course.

It is used for:
- generation of test signals;
- building digital processing chains;
- implementing DSP algorithms;
- moving from model to real hardware.

## 3. Role of Zynq7020
**Zynq7020** combines:
- an ARM processing system;
- programmable FPGA logic.

### What this gives
This makes it possible to separate tasks:

#### Processor part
Suitable for:
- system control;
- parameter setup;
- communication with external software;
- launching configurations;
- handling service logic.

#### FPGA part
Suitable for:
- stream processing;
- signal generation;
- filtering;
- digital frequency translation;
- implementing real-time chains.

### Why this matters for the course
From the start the student works not with an abstract “FPGA somewhere inside”, but with a real platform where:
- a model can be linked to hardware;
- digital logic produces a physical result;
- processing appears in a real received signal.

## 4. Role of AD9363
**AD9363** is an RF transceiver that provides:
- reception;
- transmission;
- conversion between analog and digital domains;
- work with I/Q streams.

### In the learning logic of the block
AD9363 is the link through which:
- a digital stream turns into a physical signal;
- a real signal can be obtained and then analyzed.

### What the student needs to understand
At the first stage there is no need to study all internal modes in detail. It is enough to understand that:
- there are frequency parameters;
- there are bandwidth parameters;
- there are gains and levels;
- there is a receive and a transmit chain;
- there is a connection to the digital part of the platform.

## 5. RTL-SDR as an external receiver
RTL-SDR is used in this course as:
- inexpensive;
- simple;
- illustrative;
- external observation equipment.

### Why it is needed
It allows the student to:
- quickly see the result of the experiment;
- avoid overcomplicating the first step;
- verify that the signal really exists;
- observe spectrum and waterfall;
- record data for analysis.

### Limitations of RTL-SDR
It should be understood that RTL-SDR:
- is not a high-precision measurement receiver;
- has limited dynamic range;
- is limited in bandwidth and chain quality;
- may introduce its own artifacts.

For the first educational lab, however, it is a practical and suitable tool.

## 6. The computer as part of the laboratory setup
In the course, the computer plays several roles at once:
- modeling environment;
- configuration tool;
- observation tool;
- recording tool;
- analysis tool;
- software development environment.

On one PC the student can:
- build a model;
- receive a signal;
- record IQ;
- perform MATLAB analysis;
- open the project in Python or C++;
- prepare the report.

## 7. Ways to connect the subsystems
Two basic approaches are possible:

### 1. Over the air
The signal is transmitted and received via antennas.

Advantages:
- visually intuitive;
- quick to deploy;
- fewer requirements for cable hardware.

Disadvantages:
- influence of the environment;
- interference;
- harder to obtain repeatable results;
- stronger dependence on tuning and levels.

### 2. Cable connection
The transmitter and receiver are linked directly through attenuation and adapters.

Advantages:
- high repeatability;
- less influence of the environment;
- easier execution of the laboratory work.

Disadvantages:
- careful level control is required;
- direct connection without understanding permissible power levels is not allowed.

## 8. Importance of level control
One of the main rules when working with RF equipment is:
**never connect transmitter and receiver directly without understanding the signal level**.

It is necessary to consider:
- allowable input level of the receiver;
- the need for attenuators;
- connection type;
- matching;
- path losses.

In Block 1 the emphasis is on careful work and engineering discipline.

## 9. What to check before the experiment
Before the first lab, verify that:
- the SDR board is connected correctly;
- power is stable;
- RTL-SDR is recognized by the computer;
- the interconnect cables are healthy;
- the selected link type is correct — over-the-air or cable;
- the signal level will not overload the receiver;
- the software for observing the signal is ready.

## 10. Role of the breadboard and components in the course
Although the first lab is mainly focused on the SDR chain, the course as a whole also includes circuit-design work.

That is why even in Block 1 it is important to show that, besides the SDR board, the following will also be used:
- a breadboard;
- a battery or power supply;
- resistors, capacitors, transistors;
- basic digital ICs;
- simple generators and shaping circuits.

This expands the course from pure DSP to full engineering practice.

## 11. Conclusions
After studying this section, the student should understand:
- which devices are included in the training setup;
- why Zynq7020 is used;
- what role AD9363 plays;
- why RTL-SDR is needed;
- why signal levels and connection method matter;
- how the hardware is connected with future experiments.

## Review questions
1. Which devices are included in the training setup?
2. What is the difference between the processor role and the FPGA role in Zynq7020?
3. Why is AD9363 needed in the system?
4. Why is RTL-SDR convenient for the first block?
5. How does an over-the-air connection differ from a cable connection?
6. Why is signal-level control necessary?
7. What role does the computer play in the laboratory work?
