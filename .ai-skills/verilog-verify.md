# Skill: Verilog Verification

Use this skill when adding or fixing lightweight RTL blocks, testbenches and HDL smoke checks.

## Goal

Keep HDL examples small, reproducible and connected to the SDR signal chain.

## Procedure

1. Define the block role in the SDR route:
   - streaming IQ pass-through;
   - FIR/filtering;
   - mixer/NCO;
   - decimator/interpolator;
   - synchronization helper;
   - metric or capture support.
2. Define interface assumptions:
   - clock;
   - reset polarity;
   - valid/ready or sample-enable convention;
   - signedness;
   - word length;
   - scaling.
3. Add or update a minimal testbench.
4. Use deterministic input vectors when practical.
5. Check expected output numerically, not only by waveform inspection.
6. Produce VCD only when it is useful for debugging or teaching.
7. Connect the RTL behavior back to MATLAB/Python/C++ reference logic when possible.

## Testbench checklist

- deterministic stimulus;
- explicit reset sequence;
- timeout to avoid hanging CI;
- clear PASS/FAIL message;
- non-zero exit on failure;
- comments explaining signal meaning;
- no dependency on missing local-only files.

## Validation

```bash
python tools/tasks.py hdl
```

If docs reference the HDL lab:

```bash
python tools/tasks.py docs
```

## Output format

Report:

- RTL/testbench files changed;
- interface assumptions;
- expected numerical behavior;
- command used;
- waveform or VCD path if generated.

## Do not

- add vendor-specific IP to the basic educational path unless the lab explicitly compares it;
- rely only on visual waveform review;
- use random tests without a fixed seed;
- ignore fixed-point scaling and signedness;
- leave testbenches dependent on absent vector files.
