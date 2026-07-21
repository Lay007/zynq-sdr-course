# Course Evidence Map

This map gives reviewers a compact view of what is already backed by evidence and what is still planned or hardware-pending.

| Evidence area | Location | Status | What it proves | Next action |
|---|---|---|---|---|
| Flagship reviewer report | `reports/flagship_reviewer_report.md` | Available | The strongest current evidence is compressed into one reviewer-friendly story with limits and reproduction commands | Keep it synchronized after every promoted hardware or dataset proof |
| First real observation | `datasets/lab1_0_rtl_sdr_observation/` | Available through Git LFS | The course contains real-world input data, not only synthetic examples | Add generated preview plots and complete publication review |
| Lab 1.0 learner result | `reports/lab1_0_rtl_sdr_observation_example.md` | Example report added | A student can see what a minimal first report should contain | Add screenshots/metrics references after analysis refresh |
| Dataset manifest discipline | `tools/check_dataset_manifests.py`, `.github/workflows/dataset_manifests.yml` | Checker and CI workflow added | Git LFS pointers, generated-local manifests and metrics SHA256 fields can be checked automatically | Add more dataset-specific acceptance rules as datasets mature |
| QPSK replay dataset | `datasets/demo_qpsk_capture/`, `tools/generate_demo_qpsk_dataset.py`, `tools/analyze_demo_qpsk_dataset.py` | Generated-local synthetic fixture with analyzer workflow | A legally clean deterministic QPSK CI16 dataset can be regenerated, plotted and threshold-checked | Keep analyzer thresholds and report text synchronized with generated metrics |
| Block 5 HDL evidence | `reports/fpga/`, `blocks/block_05_fpga_hdl_flow/`, CI workflows | Measured signoff candidate | 29 RTL tests plus a fully routed, timing-clean and board-qualified snapshot; strategy sweep selects WNS +0.096 ns | Check repeat-build/seed stability |
| Zynq observation path | `datasets/lab6_6_zynq_rx_observation/` | Manifest/evidence path available | The hardware validation route is documented | Add more board-level measurements and clean replay artifacts |
| Integrated project evidence | `docs/final-project-dual-modem-implementation-report.md`, Labs 11.32–11.33, fabric and RTL-SDR qualification reports | Measured internal, external and two-board QPSK proof | Coarse-CFO acquires 12/12 points; retained hardware samples drive RTL regression; Lab 11.33 accepts the residual-CFO Costas fix and rejects a physically valid but live-RF-worse timing picker | Add continuous timing recovery and longer BER-vs-attenuation statistics |
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
3. Verify the selected snapshot timing margin across repeat builds or implementation seeds.
4. Promote Labs 11.32–11.33 into the filled implementation report without turning acquisition success into a continuous-BER claim.
5. Add continuous timing recovery and stable longer-duration BER-vs-attenuation captures.
