# FPGA Streaming Principles

This page summarizes practical FPGA-oriented DSP design principles used throughout the course.

## Core idea

FPGA DSP chains are typically organized as deterministic streaming pipelines.

```text
sample stream
-> processing block
-> processing block
-> output stream
```

## Important engineering topics

| Topic | Why it matters |
|---|---|
| Throughput | sustain realtime processing |
| Latency | synchronization and buffering |
| Fixed-point precision | implementation accuracy |
| Resource usage | FPGA feasibility |
| Backpressure handling | pipeline stability |

## Typical SDR processing blocks

| Block | Function |
|---|---|
| NCO | digital frequency generation |
| Mixer | frequency translation |
| FIR | filtering |
| Decimator | sample-rate reduction |
| Interpolator | sample-rate increase |
| Synchronizer | timing alignment |

## Educational objective

Students should understand how signal-processing algorithms are transformed into deterministic hardware pipelines.
