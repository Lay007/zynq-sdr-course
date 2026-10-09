# Final Project Grading Rubric

Use this page to grade Block 12 final projects in a consistent way.

## Score table

| Area | Points | Full points | Half points | No points |
|---|---:|---|---|---|
| Requirements and success criteria | 10 | numeric pass/fail criteria fixed before the work (for example "BER = 0 over ≥ 10⁴ bits at Es/N0 ≥ 12 dB") | criteria stated, but qualitative or written after the results | no criteria |
| System architecture | 10 | block diagram with sample rates, data formats and interfaces at every boundary | diagram without rates or formats | no diagram |
| Reference model | 15 | floating-point model that runs from one command and produces the reference vectors or curves | model exists but is not reproducible or not used as a reference | no model |
| Fixed-point analysis | 15 | formats written down, quantization error measured against the float model, overflow behaviour (saturate/wrap) stated and tested | formats written down, error not measured | none |
| HDL / FPGA implementation path | 15 | RTL with a self-checking testbench that compares against the model; resources or timing reported if synthesized | RTL or HDL plan without a self-checking test | none |
| Measurement or replay path | 15 | real or shipped recording analysed with its metadata; hardware runs report all attempts, not only the best | analysis on synthetic data only | none |
| Metrics and limitations | 10 | BER/EVM/SNR with the number of bits or symbols, confidence where it matters, and what the result does **not** prove | metrics without sample sizes or limits | no metrics |
| Reproducibility and report quality | 10 | another student reproduces every figure from the repository with the listed commands | most figures reproducible | figures cannot be reproduced |

## Areas that do not apply

Not every project covers every area: Project 12.2 (RF capture analysis) has no fixed-point or HDL part, Project 12.3 (FPGA DSP block) may have no radio measurement. Agree the applicable areas when the proposal is frozen, and scale the total of those areas to 100.

## Minimum passing level

A project is acceptable when it includes:

- a clear goal;
- a reproducible command or procedure;
- at least one generated figure;
- at least one metric;
- an engineering conclusion.

## Portfolio-ready level

A project is portfolio-ready when it includes model, implementation notes, measured or replayed data, metric interpretation and a clean report.
