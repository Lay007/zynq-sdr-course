# End-to-End QPSK Hardware Demo

This page defines the target flagship demonstration for the course.

## Goal

Show one traceable path from a QPSK reference model to a board-level experiment, IQ recording or replay, offline analysis and final report.

```text
reference model -> fixed-point assumptions -> HDL/FPGA path -> Zynq/AD9363 setup -> controlled RF path or replay -> IQ analysis -> report
```

## Required setup record

| Field | Value |
|---|---|
| Board | Zynq-7020 + AD9363 or compatible |
| Receiver | RTL-SDR, AD9363 RX path, or recorded dataset |
| Center frequency | TBD |
| Sample rate | TBD |
| Symbol rate | TBD |
| Roll-off | TBD |
| TX gain | TBD |
| RX gain | TBD |
| Attenuation | TBD |
| IQ format | CI16 / CU8 / CF32 / WAV IQ |

## Required artifacts

| Artifact | Suggested path |
|---|---|
| Reference model notes | `docs/` or `blocks/block_11_integrated_sdr_project/` |
| Dataset manifest | `datasets/demo_qpsk_capture/manifest.yaml` |
| Measurement report | `docs/final-project-example-report.md` |
| FPGA resource report | `reports/fpga/` |
| Safety checklist | `templates/rf_safety_checklist.template.md` |

## Acceptance criteria

- QPSK parameters are documented.
- The IQ data source is unambiguous.
- The analysis produces a constellation plot or equivalent metrics.
- EVM, SNR, BER or decision-quality metrics are reported.
- The result includes limitations and next steps.

## Upgrade path

1. Start with synthetic QPSK replay.
2. Move to conducted loopback with attenuation.
3. Add HDL block comparison.
4. Add timing and FPGA resource reports.
5. Promote the result to a final project report.
