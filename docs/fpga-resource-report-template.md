# FPGA Resource Report Template

Use this page to document synthesis, implementation, timing and latency evidence for FPGA-facing labs.

## Resource table

| Block | Device | LUT | FF | DSP | BRAM | URAM | Fmax, MHz | Latency, cycles | Notes |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| FIR IQ 4-tap | XC7Z020 | TBD | TBD | TBD | TBD | N/A | TBD | TBD | TBD |
| NCO mixer IQ | XC7Z020 | TBD | TBD | TBD | TBD | N/A | TBD | TBD | TBD |
| AXI-Stream wrapper | XC7Z020 | TBD | TBD | TBD | TBD | N/A | TBD | TBD | TBD |

## Required report fields

- FPGA device and board.
- Tool version.
- Clock constraints.
- Synthesis strategy.
- Implementation strategy.
- Timing summary.
- Resource utilization.
- Interface assumptions.
- Latency and throughput.
- Known limitations.

## Recommended source files

```text
reports/fpga/<block-name>-<device>.md
reports/fpga/<block-name>-utilization.txt
reports/fpga/<block-name>-timing.txt
```

## Review rule

A block is not hardware-ready until it has at least one of:

- simulation pass/fail evidence;
- latency estimate;
- resource estimate;
- timing report;
- board-level validation note.
