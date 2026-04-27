# Block 1. Introduction to SDR, Tools, and First Signal Reception

## Engineering route of the block

```mermaid
flowchart TB
    THEORY["1. SDR fundamentals<br/>analog vs digital chain, I/Q and DSP role"]
    SETUP["2. Environment setup<br/>RTL-SDR drivers, HDSDR, MATLAB / Simulink and Python"]
    HARDWARE["3. Hardware platform<br/>Zynq-7020 + AD9363, RTL-SDR and RF connections"]
    MODEL["4. Model to hardware bridge<br/>test tone, Fs/Fc/gain and sample stream"]
    LAB["5. First RF experiment<br/>generation, external reception and IQ recording"]
    ANALYSIS["6. Offline analysis<br/>MATLAB, Python, C++ and GNU Radio replay"]
    NEXT["7. Next steps<br/>fixed-point, FPGA and circuit design"]

    THEORY --> SETUP --> HARDWARE --> MODEL --> LAB --> ANALYSIS --> NEXT
```

## Hardware setup photos

### RTL-SDR V3 Pro

![RTL-SDR V3 Pro](/zynq-sdr-course/images/hardware/rtl_sdr_v3_pro_real.png)

### Xilinx Zynq-7020 + ADRV module

![Xilinx Zynq-7020 with ADRV module](/zynq-sdr-course/images/hardware/xilinx_7020_adrv_real.png)

## Core learning chain

**Mathematical model → fixed-point → sample stream → FPGA/SoC → physical signal → external reception → IQ recording → offline analysis**

## Practical outcome

After completing the block, the student can execute the full SDR loop:

**generation → transmission → reception → recording → analysis**
