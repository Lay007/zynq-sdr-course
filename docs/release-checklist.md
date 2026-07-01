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
python tools/run_local_ci.py --quick
```

If a local environment cannot run all tasks, document which checks were run and why the remaining checks were skipped.

## 3. Course structure review

- Main README files describe the current learning route.
- Russian and English navigation are consistent.
- New pages are linked in `mkdocs.yml`.
- Key labs include acceptance criteria.
- HDL-facing labs include self-checking testbenches where practical.
- Real-data workflows use manifests and checksums.
- Status pages remain compact; long debug histories live on evidence pages.

## 4. v0.1.0 readiness gate

| Gate | Required state |
|---|---|
| README / README_RU | Both explain the current route and link to the correct language track. |
| MkDocs | Strict build passes. |
| CI | Full smoke and block workflows are green or explicitly documented. |
| Status | `docs/status.md` is a compact readiness matrix. |
| Evidence | Evidence index and validation backlog are synchronized. |
| Reviewer path | A reviewer can find commands, evidence and open gaps within a few clicks. |
| Final project | At least one report skeleton exists; a filled flagship report is the next milestone. |

## 5. Release notes draft

Suggested release summary:

```text
v0.1.0 introduces a bilingual DSP/FPGA/SDR course that connects theory, modeling, fixed-point design, HDL simulation, SDR experiments, IQ capture and engineering analysis.
```

## 6. Final checks

- GitHub Pages workflow is green.
- New assets render correctly from the site.
- No large raw IQ captures are committed directly.
- No private data, credentials or local machine paths are committed.
- Open Dependabot PRs are either merged, closed as obsolete, or left with a clear reason.
