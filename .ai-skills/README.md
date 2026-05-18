# AI Skills for Zynq SDR Course

This directory contains reusable procedures for AI-assisted engineering work in this repository.

Use them together with `CONTEXT.md`.

## Available skills

| Skill | Use when |
|---|---|
| `diagnose.md` | CI, MkDocs, asset, HDL or lab failures need root-cause analysis |
| `make-lab.md` | creating or improving SDR/DSP/FPGA labs |
| `make-ieee-figure.md` | creating or polishing engineering figures and plots |
| `fix-ci.md` | repairing GitHub Actions or local smoke checks |
| `verify-docs-assets.md` | checking broken images, links and MkDocs navigation |
| `verilog-verify.md` | adding or fixing lightweight RTL simulations and testbenches |
| `dsp-benchmark.md` | adding executable DSP demos, measurements and benchmark-style outputs |

## Usage example

```text
Use CONTEXT.md and .ai-skills/diagnose.md.
Fix the failing MkDocs build with the smallest safe change.
Show changed files and validation commands.
```

## Rules

- Keep changes small and reviewable.
- Prefer reproducible scripts over manual-only artifacts.
- Preserve the route: theory -> modeling -> fixed-point -> HDL/FPGA -> RF -> measurement.
- Do not make broad rewrites unless explicitly requested.
- Always report what was checked and what was not checked.
