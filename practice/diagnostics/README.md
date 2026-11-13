# SDR diagnostic challenges

Four deliberately faulty exercises for [issue #85](https://github.com/Lay007/zynq-sdr-course/issues/85).
Record a prediction, measure the symptom, fix your own copy and rerun the same checks.

- [English guide](../../docs/en/diagnostic-challenges.md)
- [Русское руководство](../../docs/ru/diagnostic-challenges.md)
- `manifest.json`: case IDs, prerequisites, tools and evidence level.
- `starter.py`, `rtl/axis_drop.v`: learner starting points, intentionally incorrect.
- `reference.py`, `mutants.py`, `rtl/axis_duplicate.v`: instructor controls.
- `check.py`: grader, JSON metrics and workspace initialization.
- `rtl/tb_axis_diagnostic.sv`: transaction scoreboard, stalls, bubbles and reset during a pending transfer.

From the repository root, with the course Python dependencies installed:

```bash
python practice/diagnostics/check.py init build/my-diagnostics
python practice/diagnostics/check.py check --case cfo --implementation build/my-diagnostics/learner.py --output build/my-diagnostics/cfo-before.json
```

The untouched learner implementation must fail with exit code 1. Edit only the
workspace copy. Exit code 0 means the selected implementation passed the specified
cases; 2 means a command/tool/implementation error. A compile error is not a
successful negative-control experiment. `init` refuses an existing directory.

Instructor verification (Icarus Verilog and `vvp` required for `--with-rtl`):

```bash
python practice/diagnostics/check.py self-test --with-rtl --output build/diagnostics-controls.json
```

This checks four passing references and ten rejected faulty implementations.
It does not record student progress or hardware validation. Software and RTL
checks can run separately with `self-test` and `self-test --rtl-only`.

The AXI reference is the existing Lab 5.4 module, not a second production RTL
implementation. These exercises do not depend on the separate FIR/Q15 practice
pilot in PR #88. All samples are generated locally; no RF transmitter, IQ archive,
MATLAB license or vendor FPGA toolchain is needed.
