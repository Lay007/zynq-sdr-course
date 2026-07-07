# Course Evidence Map

This map gives reviewers a compact view of what is already backed by evidence and what is still planned or hardware-pending.

| Evidence area | Location | Status | What it proves | Next action |
|---|---|---|---|---|
| Flagship reviewer report | `reports/flagship_reviewer_report.md` | Available | The strongest current evidence is compressed into one reviewer-friendly story with limits and reproduction commands | Keep it synchronized after every promoted hardware or dataset proof |
| First real observation | `datasets/lab1_0_rtl_sdr_observation/` | Available through Git LFS | The course contains real-world input data, not only synthetic examples | Add generated preview plots and complete publication review |
| Lab 1.0 learner result | `reports/lab1_0_rtl_sdr_observation_example.md` | Example report added | A student can see what a minimal first report should contain | Add screenshots/metrics references after analysis refresh |
| Dataset manifest discipline | `tools/check_dataset_manifests.py`, `.github/workflows/dataset_manifests.yml` | Checker and CI workflow added | Git LFS pointers, generated-local manifests and metrics SHA256 fields can be checked automatically | Add more dataset-specific acceptance rules as datasets mature |
| QPSK replay dataset | `datasets/demo_qpsk_capture/`, `tools/generate_demo_qpsk_dataset.py`, `tools/analyze_demo_qpsk_dataset.py` | Generated-local synthetic fixture with analyzer workflow | A legally clean deterministic QPSK CI16 dataset can be regenerated, plotted and threshold-checked | Keep analyzer thresholds and report text synchronized with generated metrics |
| Block 5 HDL evidence | `reports/fpga/`, `blocks/block_05_fpga_hdl_flow/`, CI workflows | Available with signoff gap | 18 RTL tests and paired standalone/snapshot implementation reports | Produce one flow that both closes timing and passes board qualification |
| Zynq observation path | `datasets/lab6_6_zynq_rx_observation/` | Manifest/evidence path available | The hardware validation route is documented | Add more board-level measurements and clean replay artifacts |
| Integrated project evidence | `docs/final-project-dual-modem-implementation-report.md`, `reports/hardware/qpsk-fabric-loopback-qualification-20260707.md` | Measured internal QPSK proof | QPSK reaches BER=0 across 5/5 boot sessions and 14/14 selected-offset attempts | Add external RF metrics and close implementation timing correlation |
| Reviewer process | `docs/reviewer-checklist.md`, `docs/status.md`, `docs/lab-index.md` | Available | Reviewers can evaluate reproducibility, DSP, HDL and measurement evidence | Keep the status matrix synchronized after every promotion |

## Immediate quality gates

Run these commands from a clean checkout when reviewing repository health:

```bash
python tools/tasks.py docs
python tools/tasks.py labs
python tools/generate_demo_qpsk_dataset.py --metadata-only
python tools/check_dataset_manifests.py
```

Run HDL checks when Icarus Verilog is available:

```bash
python tools/tasks.py hdl
```

## Current highest-value gaps

1. Add preview plots and metrics for the Lab 1.0 real-data captures.
2. Keep the generated QPSK dataset, analyzer outputs and documentation synchronized.
3. Resolve the split between the timing-clean standalone flow and hardware-working snapshot flow.
4. Extend the filled implementation report with publication-cleared RF measurements.
