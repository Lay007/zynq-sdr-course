# Project 12.3 — FPGA DSP Block Final Project

## Goal

Implement or extend one DSP block for FPGA use, verify it with a self-checking testbench and compare it against a reference model.

## Candidate blocks

| Block | Suggested evidence |
|---|---|
| FIR filter | coefficient table, fixed-point error, RTL PASS |
| NCO mixer | phase accumulator settings, spectrum, RTL PASS |
| AXI-Stream wrapper | backpressure test, latency, handshake evidence |
| Decimator | anti-aliasing response, output-rate verification |

## Minimum deliverables

- reference model;
- fixed-point specification;
- RTL module or RTL extension;
- self-checking testbench;
- waveform or PASS log;
- error analysis;
- final report.

## Success criteria

| Criterion | Target |
|---|---:|
| Testbench status | PASS |
| Max error | defined by student |
| Latency documented | required |
| Fixed-point format documented | required |

## Report conclusion template

```text
The FPGA DSP block implements ______. The RTL testbench status is ____ and max error is ____.
The block is / is not ready for integration because ______.
```
