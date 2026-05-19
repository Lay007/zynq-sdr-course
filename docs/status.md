# Course status and readiness matrix

This page is the top-level engineering status board for the course. It is intentionally concise: it shows what is already strong, what is executable, and what still needs hardware validation.

## Readiness legend

| Mark | Meaning |
|---|---|
| `Ready` | The material is suitable for learners and can be used as a stable course page. |
| `Executable` | The block has scripts, tests, generated plots, or reproducible checks. |
| `Draft` | The structure exists, but the block still needs deeper theory, labs, or examples. |
| `Hardware pending` | The learning path is defined, but board-level validation or real capture data is still needed. |

## Block readiness matrix

| Block | Topic | Theory | Labs | Code / models | Figures | Hardware | CI coverage | Next improvement |
|---|---|---|---|---|---|---|---|---|
| 01 | Intro to SDR | Ready | Ready | Partial | Ready | Partial | Docs | Add a first validated RTL-SDR capture example. |
| 02 | Signals and sampling | Draft | Draft | Partial | Partial | Not required | Docs | Add executable aliasing and IQ sampling demos. |
| 03 | DSP basics | Ready | Executable | Python / MATLAB / C++ path | Ready | Not required | Labs | Add more fixed test vectors and reference outputs. |
| 04 | Simulink and fixed-point | Ready | Executable | Python / MATLAB-style references | Ready | Not required | Labs | Add Simulink screenshots and fixed-point export examples. |
| 05 | FPGA / HDL flow | Ready | Executable | Verilog testbenches | Ready | Hardware pending | HDL CI | Add board-level timing and resource reports. |
| 06 | RF frontend and AD9363 | Ready | Executable | Analysis scripts | Ready | Hardware pending | Labs | Add validated AD9363 setup and gain table. |
| 07 | TX/RX chains | Ready | Executable | DUC/DDC demos | Ready | Hardware pending | Labs | Add RF loopback measurement package. |
| 08 | Modulation and synchronization | Ready | Executable | Synchronization demos | Ready | Optional | Sync CI | Add impairment sweeps and BER/EVM dashboards. |
| 09 | Recording and analysis tools | Ready | Executable | IQ readers | Ready | Hardware pending | Recording CI | Add small public IQ demo manifests. |
| 10 | KiCad and basic electronics | Ready | Draft | Calculators / templates | Partial | Bench pending | Docs | Add measured breadboard photos and KiCad exports. |
| 11 | Integrated SDR project | Ready | Executable | Simulation package | Ready | Hardware pending | Labs | Add one complete end-to-end hardware project report. |
| 12 | Final projects | Ready | Draft | Templates | Partial | Depends on project | Docs | Add grading rubric and example final report. |

## Course-level strengths

- The repository already connects theory, DSP, fixed-point implementation, HDL, RF, IQ recording, analysis and reporting.
- The documentation site is built with MkDocs and structured for both Russian and English learners.
- Several blocks are executable and are supported by reproducible scripts, generated assets and CI workflows.
- The hardware story is clear: Zynq-7020 + AD9363/ADRV is the target SDR platform, and RTL-SDR/HDSDR is the independent observation path.

## Main gaps to close

1. Add at least one small validated IQ dataset or external dataset manifest.
2. Add board-level measurements for the Zynq/AD9363 path.
3. Add RF safety limits and attenuation assumptions to every hardware-facing lab.
4. Keep RU/EN pages aligned when adding new labs.
5. Add final report examples with plots, metadata and measurement uncertainty notes.

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
