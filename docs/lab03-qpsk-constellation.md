# Lab 3 — QPSK → Constellation → Impairments

Lab 3 introduces digital modulation and visualization through constellation diagrams.

---

## Goal

```text
bitstream → QPSK modulation → RF transmission → IQ capture → constellation → quality metrics
```

---

## Experiment flow

```mermaid
flowchart LR
    SRC["Bitstream"]
    MOD["QPSK modulator"]
    TX["Zynq + AD9363"]
    RX["RTL-SDR"]
    IQ["IQ recording"]
    CONST["Constellation plot"]
    METRICS["EVM / phase noise"]

    SRC --> MOD --> TX --> RX --> IQ --> CONST --> METRICS
```

---

## Typical impairments

| Impairment | Visual effect |
|---|---|
| Noise | cloud spreading |
| Phase offset | rotation |
| CFO | slow rotation over time |
| IQ imbalance | ellipse |
| Clipping | distorted clusters |

---

## Demo figure

![QPSK constellation](assets/lab03_constellation.png)

---

## Engineering takeaway

Constellation is a compact representation of multiple impairments at once. It is one of the most powerful diagnostic tools in SDR.
