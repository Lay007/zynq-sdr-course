# Diagnose a broken SDR chain

[Русская версия](../ru/diagnostic-challenges.md)

These four optional exercises turn a plausible-looking result into a diagnosis.
You receive an intentionally faulty implementation, record a hypothesis, measure
the failure, make a small fix and demonstrate a regression check. All evidence is
synthetic software or RTL simulation. No board, transmitter or recorded RF data is used.

| Case | Prerequisites | Observable symptom | Verification |
| --- | --- | --- | --- |
| `cfo` | [Lab 8.1](labs/lab-8-1-cfo-estimation-correction.md) | Residual frequency after correction | CFO in Hz, EVM, bit errors / compared bits |
| `iq` | [Lab 2.1](labs/lab-2-1-sampling-axis-and-interpretation.md), [Lab 9.1](labs/lab-9-1-iq-file-format-and-metadata.md) | A tone appears on the wrong side of zero | Signed spectral peak, complex error, int16 endpoints |
| `fir` | [Lab 4.1](labs/lab-4-1-fixed-point-fir.md), [Lab 5.2](labs/lab-5-2-fir-rtl-mapping.md) | Small signals pass, large signals change sign | Exact integer outputs, error in LSB |
| `axis` | [Lab 5.4](labs/lab-5-4-axis-wrapper.md) | Stalls or input gaps lose/duplicate samples | Accepted-transaction scoreboard and reset checks |

## Start with a prediction

Use Python 3.12 or newer and the course development dependencies. Activate the
environment described in the repository README, then run from the repository root:

```bash
python -m pip install -r requirements-dev.txt
python practice/diagnostics/check.py init build/my-diagnostics
```

This creates `learner.py`, `axis_iq_passthrough.v` and `report.md` in a new,
gitignored workspace. Initialization refuses to overwrite an existing directory.
Before running a case, copy the report template for that case and write:

1. What should happen, including frequency sign, numeric range or handshake cycle?
2. Which defect could explain a failure? What else could produce the same symptom?
3. Which measurement would distinguish those explanations?

Run one case at a time:

```bash
python practice/diagnostics/check.py check --case cfo --implementation build/my-diagnostics/learner.py --output build/my-diagnostics/cfo-before.json
python practice/diagnostics/check.py check --case iq --implementation build/my-diagnostics/learner.py --output build/my-diagnostics/iq-before.json
python practice/diagnostics/check.py check --case fir --implementation build/my-diagnostics/learner.py --output build/my-diagnostics/fir-before.json
python practice/diagnostics/check.py check --case axis --rtl build/my-diagnostics/axis_iq_passthrough.v --output build/my-diagnostics/axis-before.json
```

The untouched starter must fail every case. Exit codes: **0** means the selected
implementation passes, **1** means a completed check found a behavioral defect,
**2** means an invalid command, implementation exception or unavailable/failed tool.
Fix the learner copy and rerun with an `-after.json` output name. Preserve the
before/after commands and explain the change in the report. A green reference
check is not evidence that a learner completed the diagnosis.

The AXI case needs `iverilog` and `vvp` on `PATH`. On Windows, the Python cases can
run in PowerShell and RTL in WSL; WSL needs its own Python dependencies and Icarus
installation. Run from the same checkout under its `/mnt/...` path. A Windows
virtual environment cannot be reused as a Linux environment.

## Contracts and graded hints

### CFO: correction direction

The input is one complex QPSK sample per symbol at 1 MS/s, multiplied by
`exp(+j*2*pi*f*n/fs)`. The course Lab 8.1 estimator supplies `estimated_hz`.
Implement `correct_cfo(rx, estimated_hz, sample_rate_hz)` without changing sample
count or amplitude. The cases use CFO +2750, -3170 and 0 Hz, 2048 symbols each,
both without noise and with independent I/Q noise RMS 0.002, seed 85.

Checks require residual CFO magnitude below 1 Hz, EVM below 2%, and zero errors
in 4096 compared bits per case. EVM uses the known transmitted symbols without
post-hoc gain/phase alignment. These are fixed synthetic exercise limits, not
receiver sensitivity or measured RF specifications.

<details markdown="1">
<summary>Hint 1: predict</summary>

If the received phase advances by a positive angle each sample, which direction
must the correcting phasor rotate?

</details>

<details markdown="1">
<summary>Hint 2: measure</summary>

Inspect `residual_cfo_hz` before looking at the constellation. A residual near
twice the injected CFO distinguishes a wrong correction sign from no correction.
Check negative and zero CFO as well.

</details>

### IQ: ordering and conjugation

Implement `decode_iq(interleaved)` for signed int16 values in the exact order
`[I0, Q0, I1, Q1, ...]`, scaled by 32768 into complex Q1.15 samples. This exercise
starts with decoded integer values; file byte order belongs to Lab 9.1.
There are 1024 samples at 8192 samples/s, tones +1000 and -1504 Hz, amplitude 0.65
and initial phase 0.31 rad. Integer quantization is part of the stimulus.

The peak must remain at the signed input frequency and EVM must stay below 0.01%.
Separate endpoint vectors require complex error below `1e-12`, exposing signedness,
scale and ordering errors that a magnitude-only spectrum would miss.

<details markdown="1">
<summary>Hint 1: predict</summary>

What happens to `exp(j*w*n)` under complex conjugation? Does exchanging I and Q
produce exactly the same phase as conjugation?

</details>

<details markdown="1">
<summary>Hint 2: distinguish</summary>

For `z = I + j*Q`, swapping components gives `Q + j*I = j*conj(z)`.
Both operations mirror frequency; the extra quarter-turn distinguishes them.
Use complex sample error together with the signed spectral peak.

</details>

### FIR: accumulator width and Q format

Implement `fir_q15(samples, coefficients)` as a causal FIR with zero initial state.
Coefficient zero multiplies the newest sample. Return one signed integer per input,
without a filter tail. Inputs and coefficients use Q1.15. Keep the full Q2.30 sum,
round to nearest with ties toward positive infinity, then saturate to [-32768, 32767].
This matches the rounding convention of the Block 5 four-tap FIR.
The [FIR/Q15 practice pilot](../practice-fir-q15.md) uses nearest-even rounding;
its half-LSB expectations differ. Select the contract explicitly before comparing results.

The checker uses hand-derived vectors for zero input, asymmetric impulse response,
positive/negative half-LSB ties, low-level gain, both clipping rails and the
`-32768 * -32768` endpoint. Every output must match exactly. Stress coefficients
deliberately have gain above one; they test arithmetic limits, not a recommended filter.

<details markdown="1">
<summary>Hint 1: bound the sum</summary>

What is the largest positive product of two signed 16-bit values? How many signed
bits are needed for the sum of four such products? Output saturation cannot undo
accumulator overflow that happened earlier.

</details>

<details markdown="1">
<summary>Hint 2: distinguish</summary>

Four endpoint products can sum to `2**32`, requiring 34 signed accumulator bits.
Multiplying two Q1.15 numbers produces 30 fractional bits. Use a low-level input
to distinguish an incorrect shift from clipping; use full-scale cases to distinguish
accumulator wrap from final-output wrap. Python integers can retain the full sum.

</details>

### AXI: count transfers, not cycles

Edit the workspace module `axis_iq_passthrough`. It uses a single clock and a
synchronous active-low reset. Data is 32 bits, with signed 16-bit I in bits 15:0
and Q in bits 31:16; `tlast` marks every eighth accepted input. The reference is
a one-stage registered elastic buffer: one clock of latency when unstalled,
one accepted sample per clock, variable latency under backpressure. No CDC is involved.

The scoreboard samples `valid && ready` using pre-edge values, checks data/order/
`last`, and requires output valid/data/last to remain stable while stalled.
It exercises input bubbles, long and repeated output stalls, simultaneous input/
output transfers, and reset with an output pending. Reset discards buffered data;
after reset, a fresh sequence of 64 accepted samples must arrive exactly once.

<details markdown="1">
<summary>Hint 1: predict</summary>

If a full output register is stalled, can it accept another input? After an output
is consumed with no replacement input, should output valid remain high?

</details>

<details markdown="1">
<summary>Hint 2: localize</summary>

A changing stalled output suggests an overwrite. An output with no corresponding
accepted input suggests stale valid or duplication. Start at the reported cycle;
count transfers only at rising edges with both valid and ready asserted. Model
nonblocking register updates separately from the values sampled at that edge.

</details>

## Verify the exercise itself

Instructor references and deliberate mutants are separate from learner files.
The AXI reference is the existing Lab 5.4 RTL module. The instructor command checks
four passing references and ten rejected variants (eight Python, two RTL):

```bash
python practice/diagnostics/check.py self-test --with-rtl --output build/diagnostics-controls.json
python -m pytest tests/test_diagnostic_challenges.py -q
```

Use `self-test` for software only or `self-test --rtl-only` for RTL only. A missing
simulator, compilation failure or incomplete simulation does not count as a caught
mutant. The dedicated `diagnostic-challenges.yml` CI job requires both toolchains;
the general pytest run may skip the RTL test when Icarus is absent.

JSON records the checked source hash, grader hash, seed, metrics and evidence type;
RTL results also include the testbench hash, simulator version and log. Keep learner
reports local. There are no board timing/resource results, RF performance claims,
automatic certificates or proof of unrestricted correctness. These finite cases
demonstrate particular defects; they are not exhaustive verification.
