# Practice track

This is a student-facing exercise track alongside the existing SDR labs. It does not replace the reference models, hardware notebooks, or measured evidence.

## Pilot: FIR → Q15

Start with [FIR Q15 exercise](fir-q15/README.md). It has a learner starter, an independent reference, deterministic cumulative checks, and offline grading. You need Python 3.12+; no commercial DSP tool or RF board is required.

```bash
python practice/fir-q15/check.py --init work/fir-q15
python practice/fir-q15/check.py --stage 1 --path work/fir-q15
python practice/fir-q15/check.py --stage 2 --path work/fir-q15
python practice/fir-q15/check.py --stage 3 --path work/fir-q15
```

The starter intentionally fails until the learner writes the functions. The instructor-only reference can be checked separately:

```bash
python practice/fir-q15/check.py --stage 3 --solution
```

A reference pass is **not** evidence of learner completion. The tests are public regression checks, not a secure examination.

## Ground rules

- Predict expected outputs before editing code.
- Keep the original starter and reference untouched in the course checkout; write in the initialized workspace.
- Fix a failed assertion by explaining the underlying signal-processing issue.
- Record model assumptions, numeric formats, metrics, and the command actually run.
- Use existing Block 3.2, 4.1 and Block 5 labs for deeper modeling and hardware implementation. The pilot itself asserts no hardware completion.

Future challenges and site work: [#84](https://github.com/Lay007/zynq-sdr-course/issues/84), [#85](https://github.com/Lay007/zynq-sdr-course/issues/85), [#86](https://github.com/Lay007/zynq-sdr-course/issues/86), [#87](https://github.com/Lay007/zynq-sdr-course/issues/87).
