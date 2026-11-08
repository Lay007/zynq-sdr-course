# FIR → Q15: student implementation pilot

**Level:** intermediate · **Mode:** offline/simulation · **Hardware:** none · **Stages:** 3 · **Evidence:** local grader output

Existing course links: [Lab 3.2](../../docs/ru/labs/lab-3-2-fir-low-pass.md) (FIR fundamentals), [Lab 4.1](../../docs/ru/labs/lab-4-1-fixed-point-fir.md) (fixed point), and [Block 5](../../docs/ru/blocks/05-hdl-fpga-flow.md) (FPGA path).

## Problem

A causal finite impulse response filter with coefficients `h[0..M-1]` and real input `x[n]` produces one output for every input sample:

```text
y[n] = sum(h[k] * x[n-k], k=0..M-1), with x[t] = 0 for t < 0.
```

The first stage uses Python floats. The second converts real numbers to signed Q1.15 integers. The third filters signed Q1.15 samples and coefficients with **unbounded integer accumulation** in the learner model, rounds once to nearest even after division by `2**15`, then saturates to `[-32768, 32767]`. A real RTL implementation must size its accumulator explicitly.

### Stage 1 — causal FIR

Write `fir_float(samples, taps)` in the learner `starter.py`. Preserve input order, return exactly `len(samples)` outputs, treat prehistory as zero and do not alter input arrays.

### Stage 2 — quantization

Write `quantize_q15(values)`. Convert each finite real value `v` to `clip(round(v * 32768), -32768, 32767)` using nearest-even rounding. Define input and output as Python lists.

### Stage 3 — integer filtering

Write `fir_q15(samples_q15, taps_q15)`. Multiply integer samples and coefficients, sum in a wide integer accumulator, round the sum to the nearest even integer after dividing by `32768`, then saturate each output to signed int16. Return `len(samples_q15)` outputs.

The checker includes impulse, causality, endpoint saturation, ties-to-even, negative samples and a deterministic regression vector. For a physical FPGA, later compare bit-exact outputs, latency and resources with the RTL and document any departures from this mathematical integer reference.

## Commands

From the repository root:

```bash
python practice/fir-q15/check.py --init work/fir-q15
python practice/fir-q15/check.py --stage 1 --path work/fir-q15
python practice/fir-q15/check.py --stage 2 --path work/fir-q15
python practice/fir-q15/check.py --stage 3 --path work/fir-q15
```

`--stage N` runs all checks for stages 1 through N. If the student gets stuck, [hints.md](hints.md) provides progressively more explicit guidance. The solution is available for instructors and regression checks; do not paste it into the starter when teaching.

## Interpretation

Passing this exercise establishes deterministic **software** numerical behavior only. It does not establish HDL bit-exactness, AXI-Stream timing, RF validity, or FPGA implementation results. Use the existing labs to progress to those stages.
