# Model → FPGA → RF → Measurement

This page is the **core of the course**. It describes how a signal travels from a mathematical idea to a real RF waveform and back to data.

---

## End-to-end system view

```mermaid
flowchart LR
    MODEL["Model\nMATLAB / Simulink"]
    FIXED["Fixed-point\nscaling / quantization"]
    FPGA["FPGA pipeline\nDDS / mixer / FIR"]
    RF["RF TX\nAD9363"]
    CHANNEL["Channel\ncoax / air"]
    RX["External RX\nRTL-SDR"]
    IQ["IQ recording\nWAV / RAW"]
    ANALYSIS["Analysis\nFFT / EVM / BER"]
    DECISION["Engineering decision"]

    MODEL --> FIXED --> FPGA --> RF --> CHANNEL --> RX --> IQ --> ANALYSIS --> DECISION
    DECISION -. redesign .-> MODEL
    DECISION -. scaling fix .-> FIXED
    DECISION -. gain tuning .-> RF
```

---

## Engineering interpretation

| Stage | Key risk | What you verify |
|---|---|---|
| Model | wrong assumptions | spectrum, waveform |
| Fixed-point | quantization | SNR degradation |
| FPGA | architecture | real-time capability |
| RF | analog effects | distortions, gain |
| Receiver | measurement errors | independent observation |
| Analysis | wrong metrics | false conclusions |

---

## FPGA signal path

```mermaid
flowchart LR
    IN[Input samples]
    DDS[DDS / NCO]
    MIX[Mixer]
    FIR[FIR filter]
    RATE[Interpolator / Decimator]
    AXI[AXI-Stream]
    OUT[To RF frontend]

    IN --> DDS --> MIX --> FIR --> RATE --> AXI --> OUT
```

---

## SDR TX/RX chain

```mermaid
flowchart LR
    SRC[Source]
    MOD[Modulator]
    SHAPE[Pulse shaping]
    DUC[Upconversion]
    TXRF[RF TX]
    CH[Channel]
    RXRF[RF RX]
    DDC[Downconversion]
    SYNC[Sync]
    DEMOD[Demod]

    SRC --> MOD --> SHAPE --> DUC --> TXRF --> CH --> RXRF --> DDC --> SYNC --> DEMOD
```

---

## Measurement loop

```mermaid
flowchart LR
    TX[Zynq TX]
    AIR[RF path]
    RTL[RTL-SDR]
    HDSDR[HDSDR]
    FILE[IQ file]
    MATLAB[MATLAB / Python]

    TX --> AIR --> RTL --> HDSDR --> FILE --> MATLAB
    MATLAB -. feedback .-> TX
```

---

## Key takeaway

```text
Model → Hardware → Measurement → Decision
```

If any stage is skipped, the engineering result is unreliable.
