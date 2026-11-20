# FIR architecture comparison

Record the revision, commands and tool versions. Attach the metrics JSON and keep
the simulator and Vivado reports available for review.

## RTL simulation

- Sample and coefficient widths, coefficients, accumulator width and rounding rule
- Clock, reset, input handshake and output consumption assumptions
- Test seed, number of compared IQ pairs and result for each architecture
- Observed latency and initiation interval in clocks, including how they were counted

## Vivado implementation

- FPGA part, Vivado build, directives, clock period and I/O delay assumptions
- Evidence stage and routing status for each architecture

| Variant | LUT | FF | DSP48E1 | BRAM tiles | WNS (ns) | WHS (ns) | Failing path |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Parallel | | | | | | | |
| Folded | | | | | | | |
| Pipelined | | | | | | | |

## Decision

Set a sample-rate requirement and a DSP budget. Compare each schedule's rate
ceiling against that requirement and explain which timing constraints must be
met in the integrated design. Identify which conclusions rely on simulation,
out-of-context implementation or board measurements.
