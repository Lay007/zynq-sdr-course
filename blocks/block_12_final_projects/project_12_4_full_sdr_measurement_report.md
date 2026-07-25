# Project 12.4 — Full SDR Measurement Report

## Goal

Prepare a complete measurement-driven SDR report that combines modeling, implementation, RF setup, IQ recording, synchronization and metrics.

## Required report structure

| Section | Content |
|---|---|
| Requirements | goal and success criteria |
| Architecture | system diagram and data formats |
| Implementation | model, fixed-point, RTL or scripts |
| RF setup | frequencies, gains, attenuation |
| Dataset | IQ file, metadata and registry entry |
| Results | figures and metrics |
| Discussion | limitations and error sources |
| Reproducibility | commands and environment |

## Minimum deliverables

- final report;
- dataset registry entry;
- metadata JSON;
- figure set;
- metrics table;
- reproducibility commands;
- limitations and next steps.

## Pass/fail table

| Criterion | Target | Measured | Status |
|---|---:|---:|---|
| Frequency error |  |  |  |
| SNR |  |  |  |
| EVM |  |  |  |
| BER |  |  |  |
| Clipping fraction |  |  |  |

## Report conclusion template

```text
The full SDR measurement project achieved ______. The key measured results were ______.
The project meets / does not meet the defined success criteria because ______.
```

## Reference implementation (Block 11)

[Lab 11.4 — Final Measurement Report](../block_11_integrated_sdr_project/lab_11_4_final_measurement_report.md)
is a completed instance of exactly this deliverable: a full, hardware-validated SDR measurement report
for the two-board QPSK link (architecture, setup, filled pass/fail table, honest limitations,
reproducibility). Use it as a worked exemplar of the structure and the standard of evidence — the
figures, metric units, attached metadata and reproducible commands — not as the project you must copy.
