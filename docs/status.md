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
| 02 | Signals and sampling | Draft | Draft | Partial | Partial | Not required | Docs | Add executable aliasing and IQ sampling demos. |
| 03 | DSP basics | Ready | Executable | Python / MATLAB / C++ path | Ready | Not required | Labs | Add direct-vs-FFT convolution threshold demo and more reference outputs. |
| 04 | Simulink and fixed-point | Ready | Executable | Python / MATLAB-style references | Ready | Not required | Labs | Add Simulink screenshots and fixed-point export examples. |
| 05 | FPGA / HDL flow | Ready | Executable | Verilog testbenches | Ready | Hardware pending | HDL CI | Fill FPGA resource and timing reports from Vivado. |
| 06 | RF frontend and AD9363 | Ready | Executable | Analysis scripts | Ready | Hardware pending | Labs | Measure AD9363 gain and overload table. |
| 07 | TX/RX chains | Ready | Executable | DUC/DDC demos | Ready | Hardware pending | Labs | Add RF loopback measurement package. |
| 08 | Modulation and synchronization | Ready | Executable | Synchronization demos | Ready | Optional | Sync CI | Add impairment sweeps and BER/EVM dashboards. |
| 09 | Recording and analysis tools | Ready | Executable | IQ readers | Ready | Hardware pending | Recording CI | Replace manifest-only QPSK dataset with validated capture or generated fixture. |
| 10 | KiCad and basic electronics | Ready | Draft | Calculators / templates | Partial | Bench pending | Docs | Add measured breadboard photos and KiCad exports. |
| 11 | Integrated SDR project | Ready | Executable | Simulation package | Ready | Hardware pending | Labs | Complete the QPSK hardware demo report. |
| 12 | Final projects | Ready | Draft | Templates + rubric | Partial | Depends on project | Docs | Apply final-project grading rubric to one example report. |

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
- expected output files under `docs/assets`, `verification`, or a documented report path;
- a short interpretation section explaining what the figure/table proves;
- local reproduction commands;
- a CI or smoke-test hook when practical.

## Newly added hardening artifacts

- `docs/final-project-grading-rubric.md` defines scoring for Block 12 work.
- `docs/end-to-end-qpsk-hardware-demo.md` defines the flagship QPSK validation package.
- `docs/fpga-resource-report-template.md` defines FPGA resource/timing evidence.
- `docs/student-ci-grading-guide.md` defines branch and CI expectations for student work.
- `datasets/demo_qpsk_capture/manifest.yaml` reserves the first QPSK dataset contract.
- `reports/fpga/z7020-resource-summary-template.md` prepares the Z7020 resource summary.

## Course-level strengths

- The repository already connects theory, DSP, fixed-point implementation, HDL, RF, IQ recording, analysis and reporting.
- The documentation site is built with MkDocs and structured for both Russian and English learners.
- Several blocks are executable and are supported by reproducible scripts, generated assets and CI workflows.
- The hardware story is clear: Zynq-7020 + AD9363/ADRV is the target SDR platform, and RTL-SDR/HDSDR is the independent observation path.

## Main gaps to close

1. Replace the QPSK manifest-only dataset with a validated capture or generated fixture.
2. Add board-level measurements for the Zynq/AD9363 path.
3. Fill Vivado resource/timing reports for the Block 5 HDL blocks.
4. Add RF safety limits and attenuation assumptions to every hardware-facing lab.
5. Apply the grading rubric to one completed final project report.

## Priority improvements

1. Promote one complete `Model -> FPGA -> RF -> Measurement` demo to portfolio-ready status.
2. Add a small public/synthetic IQ dataset manifest for recording and replay labs.
3. Add latency and resource-estimate tables for the simplest HDL blocks.
4. Add a final-project grading rubric for instructors.
5. Keep Russian and English navigation synchronized whenever a block is promoted.

## Reviewer path

For a fast review, start with:

1. `README.md` or `README_ru.md` for the course promise.
2. `docs/model-to-measurement.md` for the end-to-end engineering route.
3. `docs/lab-index.md` for runnable or report-oriented labs.
4. `docs/reproducibility-guide.md` for local rebuild instructions.
5. This status page for readiness and remaining gaps.

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
