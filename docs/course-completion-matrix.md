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

- Block 11 now has a timing-clean, repeatable QPSK silicon payload, an ExtraTiming implementation selected at WNS +0.096 ns, and 3/3 external RTL-SDR sessions with 90/90 bursts at BER=0. It remains `🟡` because controlled-path evidence, repeat-build/seed robustness and stable longer-duration capture are still pending.
- Block 12 now has a filled dual-modem report with internal and cross-session external RF evidence. It remains below portfolio-ready until controlled-path and longer-duration statistics are measured on a stable capture backend.
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
- Publish or externally archive the measured QPSK raw WAV beside the existing manifest, plots and metrics.
- Extend the selected-frame RF result to per-burst success rates and BER/EVM distributions.

### Batch C — final portfolio layer

- Extend the filled implementation report with external burst success-rate evidence.
- Add a publication-cleared RF dataset with BER/EVM/SNR figures.
- Add screenshots of the finished measurement report and generated figures.

### Batch D — make Block 11 reviewer-friendly

- Extend the selected-frame implementation report into a statistically repeatable external model-to-measurement proof.
- Keep the detailed bring-up logs as background, not as the main reviewer path.
- Add a one-page summary table: model, implementation, capture/evidence, metrics, conclusion and limitations.
- Challenge the selected routed bitstream timing margin across repeat builds or seeds.

## Review rule

A course page should not be merged as complete if it only explains theory. Every important block should have at least one of these engineering anchors:

- executable model;
- generated figure;
- fixed-point analysis;
- HDL mapping;
- RF measurement plan;
- report task.
