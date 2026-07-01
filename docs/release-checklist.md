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
python tools/check_dataset_manifests.py
```

If a local environment cannot run all tasks, document which checks were run and why the remaining checks were skipped.

## 3. Course structure review

- Main README files describe the current learning route.
- Russian and English navigation are consistent.
- New pages are linked in `mkdocs.yml`.
- Key labs include acceptance criteria.
- HDL-facing labs include self-checking testbenches where practical.
- Data workflows use manifests and checksums.
- Status pages remain compact; long debug histories live on evidence pages.
- `docs/status.md`, `docs/maturity_matrix.md`, `docs/course-completion-matrix.md`, `docs/lab-index.md` and `reports/course-evidence-map.md` do not contradict each other.

## 4. v0.1.0 readiness gate

| Gate | Required state |
|---|---|
| README / README_RU | Both explain the current route and link to the correct language track. |
| MkDocs | Strict build passes. |
| CI | Full smoke and block workflows are green or explicitly documented. |
| Status | `docs/status.md` is a compact readiness matrix. |
| Evidence | Evidence index, evidence map and validation backlog are synchronized. |
| Completion matrix | Block 11 and Block 12 reflect current evidence, not the older empty state. |
| Reviewer path | A reviewer can find commands, evidence and open gaps within a few clicks. |
| Final project | At least one report skeleton exists; a filled flagship report is the next milestone. |
| Release notes | `docs/release-notes-v0.1.0.md` mentions current promoted evidence and remaining limitations. |

## 5. Reviewer-facing release package

Before tagging the release, prepare a compact reviewer path:

1. Start at `README.md` or `README_RU.md`.
2. Open `docs/status.md` for the current readiness matrix.
3. Open `reports/course-evidence-map.md` for proof artifacts and gaps.
4. Open `docs/block11-hardware-bringup-summary.md` for the integrated-project state.
5. Open `docs/release-notes-v0.1.0.md` for the release narrative.

## 6. Release notes draft

Suggested release summary:

```text
v0.1.0 introduces a bilingual DSP/FPGA/SDR course that connects theory, modeling, fixed-point design, HDL simulation, data capture and engineering analysis. The release includes CI-backed executable labs, dataset discipline, evidence pages and a clear roadmap toward one portfolio-ready model-to-measurement report.
```

## 7. Final checks

- GitHub Pages workflow is green.
- New assets render correctly from the site.
- No large raw IQ captures are committed directly.
- No private data, credentials or local machine paths are committed.
- Open validation issues are either still valid or have comments explaining what part was already promoted into evidence pages.
- Open Dependabot PRs are either merged, closed as obsolete, or left with a clear reason.
