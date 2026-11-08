# Practice: FIR → Q1.15

<div class="practice-intro" markdown="1">

**Write the algorithm, run the checks, explain the failure.**

This exercise is a new student-facing route alongside the existing labs. It starts with a causal FIR and ends with an integer reference suitable for later comparison with RTL.

<div class="practice-meta">
<span>EXERCISE · FIR-Q15</span><span>LEVEL · INTERMEDIATE</span><span>MODE · OFFLINE</span><span>HARDWARE · NONE</span>
</div>

</div>

## Where it fits

[Block 3.2: FIR](ru/labs/lab-3-2-fir-low-pass.md) → [Block 4.1: fixed-point FIR](ru/labs/lab-4-1-fixed-point-fir.md) → [Block 5: FPGA](ru/blocks/05-fpga-hdl-flow.md).

The exercise is self-contained and needs only Python 3.12+. MATLAB, Simulink and Zynq are **not** prerequisites for the local grader.

<div class="practice-stage-grid" markdown="1">

<div class="practice-stage" markdown="1">

**01 / Model**

Implement causal floating-point convolution. Check impulse response, signed taps and input ordering.

</div>

<div class="practice-stage" markdown="1">

**02 / Numeric format**

Quantize samples and taps to signed Q1.15 with nearest-even rounding and saturation.

</div>

<div class="practice-stage" markdown="1">

**03 / Verification**

Implement integer FIR accumulation, one final rescale, rounding and clipping. Compare with deterministic expected outputs.

</div>

</div>

## Run it locally

Clone the course repository, then from its root:

```bash
python practice/fir-q15/check.py --init work/fir-q15
python practice/fir-q15/check.py --stage 1 --path work/fir-q15
python practice/fir-q15/check.py --stage 2 --path work/fir-q15
python practice/fir-q15/check.py --stage 3 --path work/fir-q15
```

The first stage must **fail** before you implement the starter. Later stages run all earlier checks as well. If a check fails, inspect what you actually computed before reading [the graduated hints](https://github.com/Lay007/zynq-sdr-course/blob/main/practice/fir-q15/hints.md).

[View exercise sources, learner starter and grader on GitHub](https://github.com/Lay007/zynq-sdr-course/tree/main/practice/fir-q15).

## What counts as evidence?

Pass/fail results prove specific, deterministic **software** properties. They are not evidence of bit-exact RTL, timing closure, an FPGA image or real RF measurements. An engineering conclusion should name the Q format, rounding rule, overflow behavior, actual command and what remains unverified.

Next, extend the work using existing HDL and board labs instead of inventing a parallel hardware implementation.

## Coming next

The [practice and design roadmap](learning-experience-roadmap.md) tracks diagnostic challenge labs, in-browser DSP figures and an optional AI tutor. The current pilot intentionally does not claim those features are already available.
