# 05. DSP Chain in FPGA

## Why it matters
This section explains how DSP algorithms are implemented in FPGA as streaming hardware pipelines rather than sequential code.

## Core idea

```mermaid
flowchart TB
    classDef dsp fill:#DCFCE7,color:#0F172A,stroke:#16A34A;

    IN["Input samples"]:::dsp
    MIX["Mixer"]:::dsp
    FIR["FIR filter"]:::dsp
    RES["Resampler"]:::dsp
    OUT["Output stream"]:::dsp

    IN --> MIX --> FIR --> RES --> OUT
```

## Key properties

### Streaming
- one sample per clock cycle;
- continuous data flow.

### Latency
- each block adds delay;
- important for synchronization.

### Throughput
- defined by clock rate;
- can sustain real-time processing.

### Parallelism
- multiple blocks operate simultaneously;
- filters can be parallelized.

## Practical conclusion

FPGA is not a CPU. DSP here is about dataflow architecture and pipelines rather than sequential instructions.
