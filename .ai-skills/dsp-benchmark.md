# Skill: DSP Demo and Benchmark Output

Use this skill when adding executable DSP demonstrations, measurement summaries, performance-style plots or reproducibility artifacts.

## Goal

Make DSP examples measurable and credible, not only illustrative.

## Procedure

1. Define the signal-processing task:
   - FFT/spectrum;
   - FIR/filtering;
   - digital mixing;
   - decimation/interpolation;
   - synchronization;
   - IQ recording analysis;
   - EVM/BER/SNR metric.
2. Define input assumptions:
   - sample rate;
   - carrier or tone frequency;
   - bandwidth;
   - modulation;
   - noise/impairments;
   - IQ format such as CI16/CU8/CF32.
3. Provide a reference calculation.
4. Generate numerical outputs and plots.
5. Store reproducibility artifacts using existing project conventions.
6. Explain what the measurement proves.
7. Add or update a smoke check when practical.

## Metrics checklist

Use explicit definitions for:

- peak frequency;
- bandwidth;
- SNR;
- EVM;
- BER;
- error between floating-point and fixed-point paths;
- latency or sample count where relevant.

## Plot checklist

- spectrum before/after;
- constellation before/after;
- error curve;
- metric vs impairment;
- benchmark-style summary table or chart when useful.

## Validation

```bash
python tools/tasks.py labs
python tools/tasks.py docs
```

For a full local check:

```bash
python tools/tasks.py smoke
```

## Output format

Report:

- task and assumptions;
- generated artifact paths;
- key numeric result;
- validation command;
- how this supports the SDR engineering route.

## Do not

- call a plot a benchmark unless it is generated from actual measured or simulated data;
- omit sample rate or units;
- hide random seeds;
- add large binary IQ recordings directly to the repository;
- use decorative charts that do not support an engineering claim.
