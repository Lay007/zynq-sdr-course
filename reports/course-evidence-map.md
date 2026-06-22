# Course Evidence Map

This map gives reviewers a compact view of what is already backed by evidence and what is still planned or hardware-pending.

| Evidence area | Location | Status | What it proves | Next action |
|---|---|---|---|---|
| First real RF observation | `datasets/lab1_0_rtl_sdr_observation/` | Available through Git LFS | The course contains real RTL-SDR air captures, not only synthetic examples | Add generated preview plots and complete publication review |
| Lab 1.0 learner result | `reports/lab1_0_rtl_sdr_observation_example.md` | Example report added | A student can see what a minimal first SDR report should contain | Add screenshots/metrics references after analysis refresh |
| Dataset manifest discipline | `tools/check_dataset_manifests.py`, `.github/workflows/dataset_manifests.yml` | Checker and CI workflow added | Git LFS pointers, generated-local manifests and metrics SHA256 fields can be checked automatically | Add more dataset-specific acceptance rules as datasets mature |
| QPSK replay dataset | `datasets/demo_qpsk_capture/` | Generated-local synthetic fixture | A legally clean deterministic QPSK CI16 dataset can be regenerated for replay and analysis labs | Add constellation preview plots and analyzer smoke coverage |
| Block 5 HDL evidence | `reports/fpga/`, `blocks/block_05_fpga_hdl_flow/`, CI workflows | Available | RTL examples have testbenches, vectors and smoke coverage | Promote OOC evidence to routed integrated top-level reports |
| Zynq RX observation | `datasets/lab6_6_zynq_rx_observation/` | Manifest/evidence path available | The hardware validation route is documented | Add more board-level measurements and clean replay artifacts |
| Integrated SDR project | `docs/end-to-end-bpsk-reference-report.md`, Block 11 labs | Executable / hardware-pending | The model-to-report route is present | Complete a measured model-to-FPGA-to-RF result |
| Reviewer process | `docs/reviewer-checklist.md`, `docs/status.md`, `docs/lab-index.md` | Available | Reviewers can evaluate reproducibility, DSP, HDL and RF evidence | Keep the status matrix synchronized after every promotion |

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

1. Add preview plots and metrics for the Lab 1.0 RTL-SDR captures.
2. Add constellation preview plots and analyzer smoke coverage for the generated QPSK dataset.
3. Add routed top-level FPGA resource/timing reports for the integrated Zynq design.
4. Complete one final model-to-measurement report with limitations and reproducibility commands.
