# 01. Introduction to SDR

## Purpose of the section
To become familiar with the basic idea of Software Defined Radio, understand the role of digital processing in the radio chain, and prepare for the first laboratory work.

## 1. What SDR is
**Software Defined Radio (SDR)** is an approach to building radio systems in which a significant part of the radio-chain functionality is implemented in software or digital logic rather than only with analog circuits.

In SDR, many functions are moved into:
- software;
- DSP algorithms;
- FPGA/SoC platforms;
- digital models and configurations.

This makes the system flexible, reconfigurable, and convenient for a fast transition from model to implementation.

## 2. Typical SDR chain
A typical SDR system includes:

1. **Signal source**  
   This may be a useful radio signal, a test tone, a modulated sequence, noise, or an IQ recording.

2. **Analog front end**  
   This includes amplifiers, filters, mixers, matching circuits, and the receive/transmit RF path.

3. **ADC / DAC**  
   At this stage the analog signal is converted to digital form or vice versa.

4. **Digital processing**  
   This is where filtering, frequency translation, demodulation, synchronization, parameter estimation, coding, and decoding are performed.

5. **Control and analysis layer**  
   This includes the embedded processor, a PC, MATLAB, Simulink, Python, C++, GNU Radio, and software for spectrum display and recording.

## 3. Boundary between analog and digital parts
A fully digital radio does not exist: the physical world remains analog. Any SDR still has an analog part at the input and output.

A convenient view is:
- **before the ADC** — analog part of the receiver;
- **after the ADC** — digital receive processing;
- **before the DAC** — digital part of the transmitter;
- **after the DAC** — analog transmit chain.

That is why an SDR engineer should understand not only DSP, but also the basics of circuit design, RF chains, power, matching, and measurements.

## 4. Why SDR is convenient for learning DSP
SDR is especially convenient for studying digital signal processing because it lets the student quickly pass through the full engineering route:

**idea → model → implementation → real signal → observation → analysis**

The same task can be:
- modeled in Simulink;
- checked in MATLAB;
- implemented partly in FPGA;
- observed in HDSDR;
- stored as IQ data;
- analyzed again in Python or C++.

This forms the correct engineering mindset: a signal should be understood not only mathematically, but also physically.

## 5. What an I/Q signal is
In SDR, signals are often represented in **complex form**:
- **I** — in-phase component;
- **Q** — quadrature component.

These are two mutually related components of one signal shifted by 90 degrees in phase.

This representation is useful because it allows:
- baseband signal description;
- digital frequency shifting;
- building modulators and demodulators;
- convenient spectrum analysis;
- working with the complex envelope.

For the first block it is enough to understand:
- an IQ signal is not “two separate signals”, but one complex representation;
- recording IQ data makes it possible to move real experiments into offline analysis.

## 6. Why the first test signal is a tone
The first lab uses a **tone signal** because it is the simplest and most illustrative test.

Advantages of a tone:
- it is easy to find in the spectrum;
- it is easy to distinguish from noise;
- it is easy to check the frequency;
- it is easy to observe amplitude changes;
- it is easy to detect setup errors in the chain.

A tone clearly reveals:
- correct generator operation;
- frequency offset;
- mirror components;
- parasitic spectral components;
- overload or insufficient signal level.

## 7. How a tone looks in different representations
### In the time domain
A tone appears as a sinusoidal or cosine waveform.

### In the frequency domain
A tone corresponds to a pronounced narrow peak at a certain frequency.

### On the waterfall
A tone appears as a stable horizontal line.

This is why a tone is an ideal first educational signal.

## 8. Role of FPGA and SoC in SDR
This course uses a platform based on **Zynq7020**, which combines:
- an ARM processor system;
- programmable FPGA logic.

This allows tasks to be separated:
- the processor is convenient for control, configuration, and communication with the PC;
- the FPGA is convenient for real-time signal processing such as generation, filtering, DDC/DUC, interfaces, and specialized DSP blocks.

This approach is especially useful in an educational course because it lets the student see how a model gradually turns into a working hardware system.

## 9. Logic of the first block
The first block is not meant to overload the student with details of RF design and FPGA development. Its goal is to show a complete experimental cycle:

1. Understand what SDR is.
2. Get familiar with the hardware and software.
3. Form a simple test signal.
4. Receive it with an external SDR receiver.
5. Observe it in the spectrum.
6. Record IQ data.
7. Analyze the recording in several tools.

This cycle becomes the basis for the following blocks.

## 10. Conclusions
After studying this section, the student should understand:
- what SDR is;
- why digital processing is important in modern radio systems;
- why IQ data is used;
- why a tone is a convenient test signal;
- how theory is connected with a real experiment.

## Review questions
1. What is Software Defined Radio?
2. How does SDR differ from a classical radio architecture?
3. Where is the boundary between the analog and digital parts of the chain?
4. What is I/Q signal representation?
5. Why is a tone convenient as the first test signal?
6. What role does FPGA play in an SDR system?
7. Why is IQ recording important for signal analysis?

## Practical preparation for the next section
Before moving on, the student should:
- understand the basic structure of an SDR chain;
- be able to explain why external signal reception is needed;
- be ready to install the software environment and get familiar with the hardware.
