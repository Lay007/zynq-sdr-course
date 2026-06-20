# Course status and readiness matrix

This page is the top-level engineering status board for the course. It is intentionally concise: it shows what is already strong, what is executable, and what still needs hardware validation.

## Readiness legend

| Mark | Meaning |
|---|---|
| `Ready` | The material is suitable for learners and can be used as a stable course page. |
| `Executable` | The block has scripts, tests, generated plots, or reproducible checks. |
| `Draft` | The structure exists, but the block still needs deeper theory, labs, or examples. |
| `Hardware pending` | The learning path is defined, but board-level validation or real capture data is still needed. |
| `Portfolio-ready` | The block has documentation, reproducible artifacts and reviewer-friendly evidence. |

## Block readiness matrix

| Block | Topic | Theory | Labs | Code / models | Figures | Hardware | CI coverage | Next improvement |
|---|---|---|---|---|---|---|---|---|
| 01 | Intro to SDR | Ready | Ready | Partial | Ready | Partial | Docs | Add a first validated RTL-SDR capture example. |
| 02 | Signals and sampling | Ready | Executable | Python path | Ready | Not required | Labs | Add MATLAB/C++ translations and a metadata-mistake replay package. |
| 03 | DSP basics | Ready | Executable | Python / MATLAB / C++ path | Ready | Not required | Labs | Add direct-vs-FFT convolution threshold demo and more reference outputs. |
| 04 | Simulink and fixed-point | Ready | Executable | Python / MATLAB references + executable BPSK `.slx` models | Ready | Not required | Labs | Constrain the BPSK Simulink path further for HDL Coder export and integration handoff. |
| 05 | FPGA / HDL flow | Ready | Executable | Verilog testbenches + AXI-Lite-controlled Zynq-ready BPSK BER top-level + gpreg-based AD9361 overlay scaffolding + integrated CLG400 bitstream/XSA + first live gpreg timeout evidence | Ready | Hardware pending | HDL CI | Tune the live RF path until the discovery burst recovers non-zero bits, then capture BER evidence. |
| 06 | RF frontend and AD9363 | Ready | Executable | Analysis scripts | Ready | Hardware pending | Labs | Build the AD9361 RX gain/overload table from the clean-image baseline. |
| 07 | TX/RX chains | Ready | Executable | DUC/DDC demos | Ready | Hardware pending | Labs | Add RF loopback measurement package. |
| 08 | Modulation and synchronization | Ready | Executable | Synchronization demos | Ready | Optional | Sync CI | Add impairment sweeps and BER/EVM dashboards. |
| 09 | Recording and analysis tools | Ready | Executable | IQ readers | Ready | Hardware pending | Recording CI | Update QPSK dataset manifest with real checksum or synthetic generator. |
| 10 | KiCad and basic electronics | Ready | Draft | Calculators / templates | Partial | Bench pending | Docs | Add measured breadboard photos and KiCad exports. |
| 11 | Integrated SDR project | Ready | Executable | Simulation package + BPSK reference package + AXI-Lite helper + gpreg-based AD9361 burst helper + live `done+timeout` bring-up report | Ready | Hardware pending | Labs | Move from clean control-plane evidence to RF recovery: verify LO/sample-rate alignment, retune gain/start offset, and capture the first non-zero `RECEIVED_BITS`. |
| 12 | Final projects | Ready | Draft | Templates + rubric | Partial | Depends on project | Docs | Use grading rubric and example report skeleton for first final project. |

## Newly added hardening artifacts

| Artifact | Purpose |
|---|---|
| `docs/final-project-grading-rubric.md` | Consistent scoring for Block 12 final projects. |
| `docs/end-to-end-qpsk-hardware-demo.md` | Flagship QPSK model-to-measurement demo checklist. |
| `docs/end-to-end-bpsk-reference-report.md` | Executable BPSK route from MATLAB reference to fixed-point and HDL handoff. |
| `docs/fpga-resource-report-template.md` | FPGA reporting contract and expected fields. |
| `docs/block5-fpga-evidence.md` | Nav-visible digest of the current Block 5 Vivado evidence package. |
| `docs/student-ci-grading-guide.md` | Student branch and CI pass/fail workflow. |
| `docs/final-project-example-report.md` | Skeleton for a portfolio-ready SDR final report. |
| `docs/hardware-validation-backlog.md` | Separation of documentation tasks and hardware-only tasks. |
| `docs/iq-demo-dataset-manifest.md` | Dataset contract for QPSK replay/capture work. |
| `datasets/demo_qpsk_capture/manifest.yaml` | First manifest-only QPSK dataset package. |
| `hardware/7020_ad936x_sdr/boot/course_clean/autorun.sh` | Clean stock-image management overlay with fixed `eth0`, DHCP, and safe TX defaults. |
| `datasets/lab6_6_zynq_rx_observation/manifest_fm_103119454.yaml` | First clean-image Zynq RX-only CI16 hardware dataset manifest. |
| `templates/fpga_resource_report.template.md` | Reusable FPGA report template. |
| `templates/student_assignment.template.md` | Reusable student assignment template. |
| `reports/fpga/z7020-resource-summary-template.md` | First Z7020 OOC FPGA resource summary with real numbers. |
| `reports/fpga/block5-utilization-summary.md` | Per-module utilization summary for the four Block 5 HDL examples. |
| `reports/fpga/block5-timing-summary.md` | Per-module timing summary at the 100 MHz target clock. |
| `reports/fpga/block5-latency-throughput-notes.md` | One-cycle latency and throughput notes verified by testbenches. |

## CI and local quality gates

| Gate | Purpose | Expected reviewer signal |
|---|---|---|
| MkDocs build | Documentation remains buildable | Navigation and links do not silently break. |
| Full course smoke | Representative labs run from a clean checkout | Generated assets are reproducible. |
| HDL smoke | Verilog examples compile and simulate | FPGA-facing examples are not only static text. |
| Block-specific checks | Catch regressions near the edited material | Small failures are easier to locate. |

## Artifact contract for mature labs

Each mature lab should eventually provide:

- a short problem statement;
- a runnable script, HDL testbench or clearly bounded manual experiment;
- expected output files under `docs/assets`, `verification`, `datasets`, `reports`, or a documented report path;
- a short interpretation section explaining what the figure/table proves;
- local reproduction commands;
- a CI or smoke-test hook when practical.

## Course-level strengths

- The repository already connects theory, DSP, fixed-point implementation, HDL, RF, IQ recording, analysis and reporting.
- The documentation site is built with MkDocs and structured for both Russian and English learners.
- Several blocks are executable and are supported by reproducible scripts, generated assets and CI workflows.
- The hardware story is clear: Zynq-7020 + AD9363/ADRV is the target SDR platform, and RTL-SDR/HDSDR is the independent observation path.

## Main gaps to close

1. Replace the QPSK manifest-only dataset with a validated small file or external link.
2. Add board-level measurements for the Zynq/AD9363 path.
3. Promote Block 5 OOC FPGA reports to placed-and-routed top-level design data.
4. Keep RU/EN pages aligned when adding new labs.
5. Turn one QPSK or tone flow into a complete final report with plots and limitations.

## Priority improvements

1. Promote one complete `Model -> FPGA -> RF -> Measurement` demo to portfolio-ready status.
2. Add a small public/synthetic IQ dataset manifest for recording and replay labs.
3. Use the current Block 5 reports as the baseline, then add routed timing/resource deltas for the integrated design.
4. Use the final-project grading rubric for instructor evaluation.
5. Keep Russian and English navigation synchronized whenever a block is promoted.

## Reviewer path

For a fast review, start with:

1. `README.md` or `README_RU.md` for the course promise.
2. `docs/model-to-measurement.md` for the end-to-end engineering route.
3. `docs/lab-index.md` for runnable or report-oriented labs.
4. `docs/reproducibility-guide.md` for local rebuild instructions.
5. `docs/reviewer-checklist.md` for pass/fail-style evidence checks.
6. This status page for readiness and remaining gaps.

## Definition of done for a new block

A block is considered course-ready when it has:

- a clear learning goal;
- theory page in both languages;
- at least one lab or guided exercise;
- generated or reproducible figures;
- expected results and validation notes;
- references to scripts, templates or test vectors;
- hardware safety notes if RF equipment is involved;
- a place in `mkdocs.yml` navigation.
