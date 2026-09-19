# Project 12.4 — Full SDR Measurement Report

## Goal

Prepare a complete measurement-driven SDR report that combines modeling, implementation, RF setup, IQ recording, synchronization and metrics.

## Why this project matters

The other three projects each exercise one skill. This one tests whether you can hold the whole
chain together and report it honestly: a system diagram that matches what you actually built, an
RF setup someone else could reproduce, a dataset with provenance, metrics with stated
definitions, and a conclusion that follows from the numbers rather than from hope. It is the
deliverable a colleague or an employer would actually read.

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

## What each section must contain

| Section | Minimum a reviewer expects |
|---|---|
| Requirements | a falsifiable sentence and numeric targets frozen **before** the measurement |
| Architecture | one diagram; the numeric format at every interface; which parts are hardware and which are software |
| Implementation | which code produced the numbers (repository path and commit); model-versus-implementation agreement stated in numbers |
| RF setup | centre frequencies, sample rate, TX and RX gains, attenuation, cable or antenna path, and the safe-shutdown procedure; for a bench with a transmitter, evidence that it was RF-safe (a cabled attenuated path or a shielded setup) |
| Dataset | provenance, format, checksum, storage location and why the raw file is or is not in Git |
| Results | every figure has axes, units and the run it came from; every ratio comes with the raw counts it was computed from |
| Discussion | at least one limitation and one rejected hypothesis; error sources ranked by how much they could move the result |
| Reproducibility | one command that regenerates or validates the metrics without the original bench |

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

Fill the *Target* column from the frozen requirements before you measure. Status is **PASS**,
**FAIL** or **NOT MEASURED**; a criterion you could not measure is reported as such, not omitted
and not filled with a plausible number. A run that fails a target is a valid result if the
measurement is valid and the cause is localized.

## Evidence discipline

The course separates three kinds of evidence, and the report must say which one each number is:

| Kind | Meaning | How to label it |
|---|---|---|
| synthetic | produced by a model or a generated dataset | say "synthetic" next to the figure and in the manifest |
| replayed | analysis of a stored capture | give the manifest and checksum |
| measured | acquired live on hardware in this project | give the setup, the settings and the number of repeated runs |

Never present a synthetic or replayed result as a hardware measurement. Repeated runs matter:
one lucky BER of 0 over a few thousand bits says little; state how many bits were compared and
across how many independent runs (compare
[Lab 8.7](/zynq-sdr-course/en/labs/lab-8-7-snr-vs-ber-traps/)).

## Verification gates

1. **G0 — plan:** requirements, targets and the pass/fail table skeleton are committed.
2. **G1 — model:** the reference model meets the targets in simulation.
3. **G2 — implementation:** the implementation agrees with the model within a stated tolerance.
4. **G3 — setup:** the RF setup is documented and safe; a sanity capture (a known tone) confirms the
   frequency axis and the channel order.
5. **G4 — measurement:** the dataset is recorded with metadata and checksum; quality checks (DC,
   clipping) pass or their failure is explained.
6. **G5 — analysis:** metrics are computed with stated definitions and filled into the table.
7. **G6 — reproduction:** a clean checkout validates the metrics from the stored artifacts.

## Reference implementation (Block 11)

[Lab 11.4 — Final Measurement Report](/zynq-sdr-course/en/labs/lab-11-4-final-measurement-report/)
is a completed instance of exactly this deliverable: a full, hardware-validated SDR measurement report
for the two-board QPSK link (architecture, setup, filled pass/fail table, honest limitations,
reproducibility). Use it as a worked exemplar of the structure and the standard of evidence — the
figures, metric units, attached metadata and reproducible commands — not as the project you must copy.

## Final acceptance checklist

- [ ] Targets were written down before the measurement.
- [ ] Every section of the required structure is present.
- [ ] Every number is labelled synthetic, replayed or measured.
- [ ] Every ratio can be recomputed from committed raw counts.
- [ ] The RF setup and safe-shutdown procedure are documented.
- [ ] The pass/fail table has no empty Status cell; unmeasured items say **NOT MEASURED**.
- [ ] At least one limitation and one rejected hypothesis are stated.
- [ ] A clean-checkout command validates the metrics.
- [ ] The conclusion says **meets** or **does not meet** the frozen criteria.

Write the report from the
[Block 12 report template](https://github.com/Lay007/zynq-sdr-course/blob/main/blocks/block_12_final_projects/reports/report_template_en.md)
and grade it with the [final-project grading rubric](/zynq-sdr-course/final-project-grading-rubric/).

## Report conclusion template

```text
The full SDR measurement project achieved ______. The key measured results were ______.
The project meets / does not meet the defined success criteria because ______.
```
