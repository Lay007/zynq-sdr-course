# Zynq SDR Course - Block Maturity Matrix

This page summarizes the maturity of the 12-block course track. The detailed status board lives in [Course status](status.md), while this page is a compact planning view for reviewers, students and contributors.

## Maturity legend

| Status | Meaning |
|---|---|
| `ready` | Stable learner-facing material exists. |
| `executable` | Scripts, tests, generated figures or reproducible checks exist. |
| `measured` | Real hardware or real IQ evidence exists. |
| `draft` | Structure exists, but the block still needs stronger examples or reports. |
| `portfolio-target` | The block is close to a complete reviewer-facing result but still needs final packaging. |

## Block-level maturity

| Block | Topic | Status | Key artifacts | Next improvement |
|---|---|---|---|---|
| 01 | Intro to SDR | ready / measured | RTL-SDR observation, controlled tone witness, learner report path | Add compact comparison report for passive capture vs controlled tone. |
| 02 | Signals and sampling | executable | Python labs, generated figures, sampling/aliasing tasks | Add C++ bridge and metadata-mistake replay examples. |
| 03 | DSP basics | executable | FFT, FIR, mixing, decimation, MATLAB/C++ links | Add direct-vs-FFT convolution threshold demo and more fixed-point tables. |
| 04 | Simulink and fixed-point | executable | Fixed-point references and BPSK Simulink models | Tighten the HDL Coder handoff constraints. |
| 05 | FPGA / HDL flow | executable | 18 HDL tests and a fully routed integrated Zynq implementation with timing closure | Correlate the generated bitstream with repeatable board operation. |
| 06 | RF frontend and AD9363 | measured | RX-only observation, zero-IF lab, controlled tone evidence | Add gain/overload table and cabled measurement package. |
| 07 | TX/RX chains | executable | DUC/DDC demos, loopback metrics models | Add measurement package and report-ready examples. |
| 08 | Modulation and synchronization | executable | CFO, phase, timing, BER/EVM demos, OFDM mini-link | Add impairment sweeps and dashboard-style metric summaries. |
| 09 | Recording and analysis tools | executable | CI16/CU8/CF32 readers, WAV IQ path, QPSK replay analysis | Keep dataset manifests and analyzer thresholds synchronized. |
| 10 | KiCad and basic electronics | draft | RF safety, attenuator and schematic templates | Add measured bench photos and exported KiCad artifacts. |
| 11 | Integrated SDR project | measured / portfolio-target | Runtime loopback result, monitor flow, Block 11 lab chain | Convert best evidence into one final model-to-measurement report. |
| 12 | Final projects | reviewable / portfolio-target | Filled dual-modem implementation report, project briefs, rubric and template | Add repeatable QPSK and external RF measurements. |

## Review rule

A block should not be promoted to `portfolio-target` unless a reviewer can see:

1. the engineering goal;
2. executable or measurable evidence;
3. expected metrics;
4. limitations;
5. the next action needed to make the result reproducible by another engineer.
