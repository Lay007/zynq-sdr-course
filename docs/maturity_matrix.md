# Zynq SDR Course - Block Maturity Matrix

This table summarizes the status and key artifacts of each laboratory block in the zynq-sdr-course.

| Block | Status | Key Artifact | Next Step |
|---|---|---|---|
| Block 01 - Introduction | verified | README, Lab Guide | none |
| Block 02 - SDR Basics | active | MATLAB simulations | Add canonical CSV, C++ bridge |
| Block 03 - FIR DSP | active | MATLAB + C++ FIR examples | Generate canonical vector, update HDL tests |
| Block 04 - Fixed-Point | draft | MATLAB fixed-point lab | Complete lab exercises, canonical outputs |
| Block 05 - HDL Integration | active | tb_iq_passthrough, tb_fir_iq_4tap | Stabilize test vectors, CI tests, canonical CSV |
| Block 06 - AXIS IQ Passthrough | active | HDL testbench, MATLAB verification | Add canonical CSV, update README |
| Block 07 - CFO Estimation | active | MATLAB simulations, C++ reference | Add canonical vector, cross-check HDL |
| Block 08 - Advanced DSP Lab | active | MATLAB & C++ demos | Complete canonical CSV, CI plots |
| Block 09 - Python Signal Processing | active | Python scripts & plots | Add canonical outputs and regression tests |
| Block 10 - Final Project | draft | Lab instructions | Add MATLAB/C++ examples, HDL templates |

---

This maturity matrix allows students, reviewers, and contributors to quickly identify which blocks are ready, which need canonical outputs, and which require CI stabilization.