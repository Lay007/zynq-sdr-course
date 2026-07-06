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
| FPGA | 18 HDL tests plus routed integrated timing, utilization and route reports |
| Data | IQ manifests and replay commands |
| Documentation | Bilingual MkDocs course pages |
| Reviewability | Status matrix, checklist and evidence index |

## Open proof gaps

| Gap | Expected improvement |
|---|---|
| Board repeatability | Correlate the routed bitstream with clean-boot BPSK/QPSK success rates. |
| Measured QPSK dataset | Add a small publication-cleared manifest-backed RF package. |
| Final project | Extend the filled implementation report with external BER/EVM/SNR evidence. |
