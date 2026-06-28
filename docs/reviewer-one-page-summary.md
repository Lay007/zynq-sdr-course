# Reviewer One-page Summary

This page gives a short entry point for reviewing the course.

## Review path

1. Read the repository README.
2. Open [Course status](status.md).
3. Open [Course demo dashboard](demo-dashboard.md).
4. Open [Reviewer acceptance checklist](reviewer-checklist.md).
5. Open [Hardware evidence index](hardware-evidence-index.md).

## Local checks

```bash
python tools/tasks.py docs
python tools/tasks.py smoke
python tools/run_local_ci.py --quick
```

## Strong points

| Area | Evidence |
|---|---|
| DSP | Executable labs and generated plots |
| FPGA | HDL examples, testbenches and CI smoke checks |
| Data | IQ manifests and replay commands |
| Documentation | Bilingual MkDocs course pages |
| Reviewability | Status matrix, checklist and evidence index |

## Open proof gaps

| Gap | Expected improvement |
|---|---|
| Integrated reports | Add routed timing and utilization evidence. |
| Demo dataset | Add a small manifest-backed replay package. |
| Final project | Add one complete model-to-measurement report. |
