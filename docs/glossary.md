# SDR / DSP / RF glossary

This glossary keeps the course terminology consistent across Russian and English pages. It focuses on terms that appear repeatedly in SDR, DSP, FPGA, RF and IQ recording labs.

## Core SDR terms

| Term | Meaning | Course context |
|---|---|---|
| SDR | Software-Defined Radio. A radio system where signal processing and control are largely implemented in software or programmable logic. | Main course subject. |
| RF | Radio frequency. The physical high-frequency signal domain before or after mixing. | Used in AD9363, RTL-SDR and hardware labs. |
| Baseband | Signal representation around 0 Hz after frequency translation. | Most DSP algorithms operate here. |
| Complex baseband | IQ representation where a signal is represented by in-phase and quadrature components. | Used for modulation, recording and analysis. |
| IQ | In-phase and quadrature samples. | Main data format for SDR recordings. |
| LO | Local oscillator. Frequency source used for mixing between RF and baseband/intermediate frequency. | Used in frequency planning. |
| Sample rate | Number of samples per second. | Defines frequency axis and bandwidth in DSP labs. |
| Bandwidth | Frequency span occupied or processed by a system. | Used in filters, SDR configuration and measurement. |

## DSP terms

| Term | Meaning | Course context |
|---|---|---|
| FFT | Fast Fourier Transform. Efficient algorithm for spectrum estimation and frequency-domain processing. | Used in spectrum and lab plots. |
| PSD | Power spectral density. Signal power distribution over frequency. | Used for noise floor and spectrum analysis. |
| FIR | Finite impulse response filter. | Used for filtering, interpolation and decimation. |
| Window | Weighting function applied before FFT or FIR design. | Used to control sidelobes and leakage. |
| Decimation | Reducing sample rate after filtering. | Used in receiver chains and analysis. |
| Interpolation | Increasing sample rate, usually before filtering or transmission. | Used in transmitter chains. |
| DDC | Digital downconverter. Translates and filters a signal to lower frequency or baseband. | Used in RX chains. |
| DUC | Digital upconverter. Translates and filters a signal toward a higher sample rate or carrier offset. | Used in TX chains. |
| NCO | Numerically controlled oscillator. Digital oscillator used for mixing. | Used in FPGA and DSP labs. |
| Quantization | Mapping continuous or high-precision values to finite precision. | Used in fixed-point analysis. |
| Fixed-point | Numeric format with a fixed number of integer and fractional bits. | Bridge from model to HDL/FPGA. |

## Modulation and synchronization terms

| Term | Meaning | Course context |
|---|---|---|
| AM | Amplitude modulation. | Early spectrum examples. |
| FM | Frequency modulation. | Early spectrum examples. |
| QPSK | Quadrature phase-shift keying. | Constellation, EVM and synchronization labs. |
| OFDM | Orthogonal frequency-division multiplexing. | Advanced mini-link and final project path. |
| CFO | Carrier frequency offset. Frequency mismatch between transmitter and receiver. | Synchronization labs. |
| Phase offset | Constant phase rotation between expected and received symbols. | Constellation correction. |
| Timing recovery | Estimating correct symbol sampling instants. | Receiver synchronization. |
| Preamble | Known sequence used for detection, synchronization or channel estimation. | Packet receiver labs. |
| BER | Bit error rate. Ratio of incorrect bits to total received bits. | End-to-end link quality metric. |
| EVM | Error vector magnitude. Distance between ideal and measured constellation points. | Modulation quality metric. |
| SNR | Signal-to-noise ratio. Ratio between signal power and noise power. | Used in measurement and link analysis. |

## FPGA / HDL terms

| Term | Meaning | Course context |
|---|---|---|
| HDL | Hardware description language, such as Verilog or VHDL. | FPGA implementation blocks. |
| RTL | Register-transfer level hardware description. | Used for Verilog modules and testbenches. |
| Testbench | Simulation environment that drives and checks an HDL module. | Used in Block 5. |
| AXI-Stream | Streaming interface commonly used in FPGA signal processing chains. | Used for DSP block integration. |
| Latency | Delay between input and corresponding output. | Important for streaming DSP and synchronization. |
| Throughput | Amount of data processed per unit time. | Used for FPGA and system-level evaluation. |
| Resource usage | LUT, FF, BRAM, DSP slice consumption. | Used for implementation trade-offs. |

## RF and measurement terms

| Term | Meaning | Course context |
|---|---|---|
| Attenuator | Passive component that reduces signal power by a known amount. | Required for safe conducted RF experiments. |
| Gain staging | Choosing gains across TX, RF path and RX to avoid overload and poor SNR. | Used in AD9363 and RTL-SDR labs. |
| Noise floor | Baseline noise level visible in spectrum. | Used for receiver and capture quality. |
| Clipping | Signal amplitude exceeding ADC or numeric range. | Indicates overload or wrong scaling. |
| DC offset | Unwanted constant component at zero frequency. | Common in IQ receivers. |
| IQ imbalance | Amplitude or phase mismatch between I and Q paths. | Advanced receiver quality metric. |
| Loopback | Feeding transmitter output back to receiver through a controlled path. | Used in board-level validation. |
| OTA | Over-the-air. Wireless path through antennas. | Use carefully and legally. |

## IQ file formats

| Format | Meaning | Notes |
|---|---|---|
| CI16 | Complex signed 16-bit integer IQ samples, usually interleaved I,Q. | Good for efficient recordings. |
| CU8 | Complex unsigned 8-bit integer IQ samples. | Common for RTL-SDR raw data. |
| CF32 | Complex 32-bit floating-point IQ samples. | Convenient for analysis, larger files. |
| WAV IQ | IQ samples stored in a WAV container. | Useful when software exports audio-like IQ files. |

## Recommended translation consistency

| English | Russian recommendation |
|---|---|
| sample rate | частота дискретизации |
| bandwidth | полоса |
| complex baseband | комплексная baseband-модель / комплексная низкочастотная модель |
| fixed-point | fixed-point / фиксированная точка |
| testbench | testbench / тестовое окружение |
| RF frontend | радиотракт / RF frontend |
| measurement report | измерительный отчёт |
| reproducibility | воспроизводимость |
| dataset manifest | manifest набора данных / dataset manifest |

## Style rule

Prefer the English acronym when it is standard in SDR literature, and explain it once in Russian text. Examples: CFO, EVM, BER, IQ, DDC, DUC, NCO, HDL, RTL.
