# Datasets

This directory stores lightweight dataset manifests and small synthetic fixtures for the course.

## Policy

- Do not commit large raw IQ recordings directly.
- Prefer manifests, checksums and external storage links for real captures.
- Use small synthetic data only when it is useful for tests or documentation.
- Keep every dataset connected to a lab, report or reproducibility guide.

## Current datasets

| Dataset | Purpose |
|---|---|
| `demo_qpsk_capture` | QPSK replay and future hardware validation package |
| `lab1_0_rtl_sdr_observation` | Git LFS-backed package for two short RTL-SDR WAV IQ captures from the first bring-up session |

## Recommended workflow

```text
manifest -> locate or generate data -> verify checksum -> run analysis -> save plots -> write report
```
