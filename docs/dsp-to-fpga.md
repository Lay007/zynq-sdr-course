# DSP → FPGA Bridge

This page connects modeling with hardware implementation.

---

## Flow

```mermaid
flowchart LR
    MODEL["Floating-point model<br/>reference MATLAB / Simulink behavior"]
    FIXED["Fixed-point model<br/>scaling, quantization and overflow margins"]
    HDL["HDL design<br/>pipeline, latency and resource mapping"]
    FPGA["FPGA implementation<br/>timing closure and real-time constraints"]
    MEASURE["RF measurement<br/>hardware validation and feedback loop"]

    MODEL --> FIXED --> HDL --> FPGA --> MEASURE
    MEASURE -. refine algorithm .-> MODEL
```

---

## Key problems

| Stage | Problem |
|---|---|
| Fixed-point | quantization noise |
| HDL | latency / pipeline |
| FPGA | timing closure |
| RF | distortion |

---

## Engineering takeaway

Bridging DSP and FPGA is the hardest and most valuable part of SDR engineering.
