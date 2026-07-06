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
| 05. FPGA / HDL flow | 🟡 | 🟡 | ⬜ | ⬜ | 🟡 | ✅ | ⬜ | 🟡 | 🟡 |
| 06. RF frontend and AD9363 | 🟡 | 🟡 | ⬜ | ⬜ | N/A | ⬜ | 🟡 | 🟡 | 🟡 |
| 07. TX/RX chains | 🟡 | 🟡 | ⬜ | ⬜ | 🟡 | ⬜ | 🟡 | 🟡 | 🟡 |
| 08. Modulation and synchronization | 🟡 | 🟡 | 🟡 | ⬜ | 🟡 | ⬜ | ⬜ | 🟡 | 🟡 |
| 09. Recording and analysis tools | 🟡 | ✅ | 🟡 | ⬜ | N/A | N/A | 🟡 | ✅ | 🟡 |
| 10. KiCad and basic electronics | 🟡 | N/A | N/A | N/A | N/A | N/A | 🟡 | ⬜ | 🟡 |
| 11. Integrated SDR project | 🟡 | ✅ | 🟡 | ⬜ | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 |
| 12. Final projects | 🟡 | N/A | N/A | N/A | N/A | 🟡 | 🟡 | ⬜ | 🟡 |

## Interpretation notes

- Block 11 is no longer empty: it has a long executable bring-up chain, a promoted internal loopback result and monitor/replay tooling. It remains `🟡` in several columns because the course still needs one polished final report that a reviewer can follow without reading the whole bring-up history.
- Block 12 has templates, rubrics and project briefs, but still needs one fully filled portfolio-grade example.
- Blocks 05 and 09 are the strongest automation anchors today: they combine reusable checks, generated artifacts and CI coverage.

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

- Keep the existing AD9363 frequency-plan, gain/bandwidth checklist and RTL-SDR capture guide synchronized.
- Run the safe cabled loopback and AD9363 gain/overload characterization.
- Add a publication-reviewed measured QPSK capture beside the existing deterministic synthetic replay.
- Record clean-boot BPSK/QPSK success rates instead of promoting a best-of-N attempt.

### Batch C — final portfolio layer

- Add final project brief.
- Add final report template.
- Add example engineering conclusion page.
- Add screenshots of a finished report and generated figures.

### Batch D — make Block 11 reviewer-friendly

- Create one short model-to-measurement report from the best current evidence.
- Keep the detailed bring-up logs as background, not as the main reviewer path.
- Add a one-page summary table: model, implementation, capture/evidence, metrics, conclusion and limitations.
- Promote routed implementation reports for the exact integrated design.

## Review rule

A course page should not be merged as complete if it only explains theory. Every important block should have at least one of these engineering anchors:

- executable model;
- generated figure;
- fixed-point analysis;
- HDL mapping;
- RF measurement plan;
- report task.
