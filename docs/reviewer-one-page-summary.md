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
| FPGA | 29 HDL tests plus routed integrated timing, utilization and route reports |
| Data | IQ manifests and replay commands |
| Documentation | Bilingual MkDocs course pages |
| Reviewability | Status matrix, checklist and evidence index |

## Open proof gaps

| Gap | Expected improvement |
|---|---|
| Board repeatability | Extend the selected RTL-SDR frame to per-burst BER/EVM success statistics. |
| Measured QPSK dataset | The synthetic zero-BER replay fixture is now public through Git LFS; publish or externally archive the separate local-only measured WAV already backed by a manifest and SHA256. |
| Final project | Add a controlled cabled comparison and timing-margin repeat builds. |
