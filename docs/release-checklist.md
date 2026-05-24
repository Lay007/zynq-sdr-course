# Release checklist

Use this checklist before publishing a public release of `zynq-sdr-course`.

## 1. Documentation build

```bash
python tools/tasks.py install
python tools/tasks.py docs
```

The MkDocs build should run in strict mode through CI.

## 2. Course smoke path

```bash
python tools/tasks.py labs
python tools/tasks.py hdl
python tools/tasks.py smoke
```

If a local environment cannot run all tasks, document which checks were run and why the remaining checks were skipped.

## 3. Course structure review

- Main README files describe the current learning route.
- Russian and English navigation are consistent.
- New pages are linked in `mkdocs.yml`.
- Key labs include acceptance criteria.
- HDL-facing labs include self-checking testbenches where practical.
- RF-facing labs include RF-safety notes.
- Real-data workflows use manifests and checksums.

## 4. Release notes draft

Suggested release summary:

```text
v0.1.0 introduces a bilingual DSP/FPGA/SDR course that connects theory, modeling, fixed-point design, HDL simulation, SDR hardware experiments, IQ capture and engineering analysis.
```

## 5. Final checks

- GitHub Pages workflow is green.
- New assets render correctly from the site.
- No large raw IQ captures are committed directly.
- No private data, credentials or local machine paths are committed.
