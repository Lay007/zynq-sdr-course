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
| `lab6_6_zynq_rx_observation` | Git LFS-backed short Zynq AD9361 receive-only CI16 capture from the clean-image baseline |
| `lab6_8_zynq_ota_tone_observation` | Git LFS-backed short Zynq AD9361 stock-shell over-the-air DDS tone capture with manifest-guided offline analysis |

## Recommended workflow

```text
manifest -> locate or generate data -> verify checksum -> run analysis -> save plots -> write report
```
