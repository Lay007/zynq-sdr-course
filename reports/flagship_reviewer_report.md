# Flagship Reviewer Report

This report is the compact portfolio entry point for `zynq-sdr-course`. It turns the current repository evidence into a single reviewer-friendly story: what has been implemented, how it is checked, what is still hardware-pending, and how to reproduce the main quality gates.

## Executive summary

`zynq-sdr-course` is an educational SDR engineering workspace that connects signal theory, DSP modeling, fixed-point thinking, HDL smoke verification, Zynq/AD936x hardware bring-up, IQ recording discipline, and engineering reporting.

The strongest current result is not one isolated script or figure. It is the reproducible route:

```text
theory -> DSP model -> fixed-point notes -> HDL/FPGA checks -> RF/IQ workflow -> metrics -> report
```

This is the main reviewer claim: the course teaches students to treat SDR work as an engineering system, not as disconnected experiments.

## Implementation summary

| Area | Current evidence | Why it matters |
|---|---|---|
| Course structure | `README.md`, `docs/course-map.md`, `docs/student-path.md`, `docs/reviewer-path.md` | A reviewer can quickly understand the learning route and the portfolio intent. |
| DSP foundations | Block 3 labs, generated plots, reproducible scripts | FFT, FIR, windows, mixing, decimation and analysis are introduced as executable material. |
| Fixed-point bridge | Block 4 labs and fixed-point workflow notes | Students see why scaling, saturation and quantization matter before RTL. |
| HDL / FPGA flow | Block 5 labs, Verilog smoke tests and FPGA reports | The course does not stop at floating-point models; selected blocks have hardware-facing checks. |
| Integrated implementation | Paired Vivado reports and machine-readable metrics | The current evidence exposes the signoff gap: standalone timing passes, while the hardware-working snapshot fails timing. |
| RF and measurement workflow | Block 6/7 materials, IQ metadata, dataset manifests | RF experiments are framed with gain staging, attenuation, capture metadata and safety notes. |
| Synchronization and link metrics | Block 8 materials, BER/EVM/SNR terminology and acceptance rules | Digital link quality is judged by recovered bits and constellation quality, not by SNR alone. |
| Data discipline | `datasets/`, `tools/check_dataset_manifests.py`, Git LFS-aware manifest checks | IQ captures can be reviewed without turning the repository into an uncontrolled data dump. |
| Reviewer process | `docs/reviewer-checklist.md`, `reports/course-evidence-map.md`, `docs/status.md` | Reviewers can separate proven evidence from hardware-pending work. |

## Key evidence links

| Evidence | Location | Reviewer question answered |
|---|---|---|
| Fast repository overview | `README.md` | What is the project and why does it matter? |
| Visual learning route | `docs/course-map.md` | How does a student move from basics to final project? |
| Reviewer route | `docs/reviewer-path.md` | What should a technical reviewer open first? |
| Evidence map | `reports/course-evidence-map.md` | Which parts are already backed by artifacts? |
| Local reproducibility | `docs/reproducibility-guide.md` | How can checks be rebuilt locally? |
| HDL smoke verification | `docs/verification/hdl_smoke.md` | Which RTL-facing examples are smoke-tested? |
| Dataset policy | `docs/real-data-policy.md` | How are real IQ captures handled safely? |
| Final project rubric | `docs/final-project-grading-rubric.md` | What counts as an acceptable engineering result? |
| Filled implementation report | `docs/final-project-dual-modem-implementation-report.md` | How do the model, RTL, routed design and current hardware evidence fit together? |

## Metric and acceptance view

| Metric / gate | Role in the course | Current expectation |
|---|---|---|
| SNR | Shows whether the signal is visible above noise | Useful diagnostic metric, but not a final digital-link acceptance criterion by itself. |
| EVM | Shows constellation quality and implementation impairment | Required for QPSK/BPSK-style modulation quality discussions. |
| BER | Shows whether bits were actually recovered correctly | Primary end-to-end digital-link acceptance metric. |
| FER / CRC status | Shows packet-level reliability when framing is available | Useful extension for packet receiver labs. |
| HDL smoke tests | Catch interface, vector and basic RTL/model mismatch problems | Must remain green before promoting FPGA-facing examples. |
| Dataset manifest checks | Catch missing metadata, bad checksums and uncontrolled data references | Must remain green for reproducible IQ evidence. |
| MkDocs strict build | Catches broken documentation navigation and links | Must remain green before publishing the course site. |

A central course rule is that SNR alone can be misleading. A high-SNR capture may still fail because of CFO, timing error, phase ambiguity, clipping, IQ imbalance, wrong bit mapping or frame-sync failure. For digital communication labs, the promoted result should include BER or packet-level evidence whenever possible.

## Reproducibility commands

Run these from a clean checkout:

```bash
python tools/tasks.py install
python tools/tasks.py docs
python tools/tasks.py labs
python tools/generate_demo_qpsk_dataset.py --metadata-only
python tools/check_dataset_manifests.py
```

When Icarus Verilog is available, also run:

```bash
python tools/tasks.py hdl
```

For a broader local preflight before larger changes:

```bash
python tools/run_local_ci.py
```

For a faster preflight:

```bash
python tools/run_local_ci.py --quick
```

## Known limitations

| Limitation | Current impact | Next evidence step |
|---|---|---|
| No single bitstream both closes timing and passes board qualification | QPSK fabric BER is repeatable, but only on the snapshot with WNS -1.676 ns | Close snapshot timing or restore runtime clocks in the timing-clean flow. |
| Some real hardware captures require local board access | Reviewers can inspect workflow and manifests, but cannot fully reproduce RF capture without hardware | Add a small publication-cleared QPSK or tone dataset with preview plots and metrics. |
| AD9363 gain/overload table is still measurement-pending | RF gain recommendations remain conservative | Measure gain staging, overload signs, clipping thresholds and recommended safe starting values. |
| The filled final report still lacks a publication-cleared QPSK RF capture | The implementation story is reviewable, but not yet a complete external model-to-measurement proof | Add manifest-backed RF data, plots, BER/EVM/SNR and uncertainty notes. |

## Reviewer conclusion

The repository is already useful as a public engineering portfolio and as a teaching workspace. Its strongest value is the discipline it demonstrates: every SDR result is expected to connect a model, an implementation, a measurement or dataset, a metric, and a written conclusion.

The next maturity step is to promote one board-level result into a complete final report with a small clean dataset, preview plots, BER/EVM/SNR table, hardware settings and exact reproduction commands.
