# DSP → FPGA Bridge

This page connects modeling with hardware implementation.

---

## Flow

```mermaid
flowchart LR
    MODEL["Floating-point model"]
    FIXED["Fixed-point model"]
    HDL["HDL design"]
    FPGA["FPGA implementation"]
    MEASURE["RF measurement"]

    MODEL --> FIXED --> HDL --> FPGA --> MEASURE
    MEASURE -. refine .-> MODEL
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
