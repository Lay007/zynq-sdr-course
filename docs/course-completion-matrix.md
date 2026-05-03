# Course completion matrix

This matrix shows what each course block should contain before it can be considered complete. It is intended for course planning, GitHub issue tracking and quick repository review.

## Legend

| Mark | Meaning |
|---|---|
| ✅ | Complete and connected to the course |
| 🟡 | Partially complete or needs polishing |
| ⬜ | Planned / missing |
| N/A | Not applicable |

## Block-level matrix

| Block | Theory | Python | MATLAB | C++ | Fixed-point | HDL / FPGA | RF / measurement | Plots | Report task |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 01. Intro to SDR | ✅ | N/A | N/A | N/A | N/A | N/A | 🟡 | ✅ | 🟡 |
| 02. Signals and sampling | 🟡 | 🟡 | 🟡 | ⬜ | ⬜ | ⬜ | 🟡 | 🟡 | ⬜ |
| 03. DSP basics | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | ⬜ | 🟡 | 🟡 |
| 04. Simulink and fixed-point | 🟡 | N/A | 🟡 | ⬜ | 🟡 | 🟡 | ⬜ | 🟡 | 🟡 |
| 05. FPGA / HDL flow | 🟡 | ⬜ | ⬜ | ⬜ | 🟡 | 🟡 | ⬜ | ⬜ | ⬜ |
| 06. RF frontend and AD9363 | 🟡 | ⬜ | ⬜ | ⬜ | N/A | ⬜ | 🟡 | ⬜ | ⬜ |
| 07. TX/RX chains | 🟡 | ⬜ | ⬜ | ⬜ | 🟡 | ⬜ | 🟡 | ⬜ | ⬜ |
| 08. Modulation and synchronization | 🟡 | 🟡 | 🟡 | ⬜ | 🟡 | ⬜ | ⬜ | 🟡 | ⬜ |
| 09. Recording and analysis tools | 🟡 | 🟡 | 🟡 | ⬜ | N/A | N/A | 🟡 | 🟡 | 🟡 |
| 10. KiCad and basic electronics | 🟡 | N/A | N/A | N/A | N/A | N/A | 🟡 | ⬜ | ⬜ |
| 11. Integrated SDR project | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 12. Final projects | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |

## Lab-level quality gates

| Gate | Requirement | Evidence in repository |
|---|---|---|
| G1 | Lab has a clear engineering objective | Lab markdown page |
| G2 | Input and output signals are specified | Parameter table |
| G3 | Reference model exists | Python and/or MATLAB script |
| G4 | Figures are reproducible | Script + generated image |
| G5 | Metrics are defined | SNR, EVM, BER, frequency error or implementation error |
| G6 | Hardware relevance is stated | Fixed-point/FPGA/RF section |
| G7 | Measurement workflow exists | IQ metadata file or capture plan |
| G8 | Report task is included | Report checklist or template link |

## Recommended next content batches

### Batch A — make Block 3 complete

- Finish FIR, mixer and decimation labs with Python + MATLAB + C++ reference code.
- Add fixed-point tables for coefficient width, input width and accumulator growth.
- Add FPGA mapping diagrams for FIR, NCO/mixer and decimator.
- Add IEEE-style comparison plots: floating point vs fixed point.

### Batch B — connect RF hardware

- Add AD9363 frequency-plan page.
- Add gain and bandwidth setup checklist.
- Add RTL-SDR/HDSDR capture guide.
- Add one example metadata JSON file for a real or synthetic IQ capture.

### Batch C — final portfolio layer

- Add final project brief.
- Add final report template.
- Add example engineering conclusion page.
- Add screenshots of a finished report and generated figures.

## Review rule

A course page should not be merged as complete if it only explains theory. Every important block should have at least one of these engineering anchors:

- executable model;
- generated figure;
- fixed-point analysis;
- HDL mapping;
- RF measurement plan;
- report task.
