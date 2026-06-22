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
| 01 | Intro to SDR | Ready | Ready | Partial | Ready | Real RTL-SDR captures available | Docs | Add a short learner report example based on the real RTL-SDR Git LFS recordings and review the publication/legal status of the narrowband capture. |
| 02 | Signals and sampling | Ready | Executable | Python path | Ready | Not required | Labs | Add MATLAB/C++ translations and a metadata-mistake replay package. |
| 03 | DSP basics | Ready | Executable | Python / MATLAB / C++ path | Ready | Not required | Labs | Add direct-vs-FFT convolution threshold demo and more reference outputs. |
| 04 | Simulink and fixed-point | Ready | Executable | Python / MATLAB references + executable BPSK `.slx` models | Ready | Not required | Labs | Constrain the BPSK Simulink path further for HDL Coder export and integration handoff. |
| 05 | FPGA / HDL flow | Ready | Executable | Verilog testbenches + AXI-Lite-controlled Zynq-ready BPSK BER top-level + gpreg-based AD9361 overlay scaffolding + integrated CLG400 bitstream/XSA + live proof that only the extracted `BOOT.bin::system_top.bit` partition currently survives external `fpga load`, while the source-correlated no-OS reference payload still times out AD9361 and the saved vendor `zc702.xpr` snapshot remains a zero-drift editable XSA baseline rather than a boot-safe RF shell | Ready | Hardware pending | HDL CI | Explain why the stock partition survives external load, then reproduce those properties in an editable shell before grafting the course overlay there. |
| 06 | RF frontend and AD9363 | Ready | Executable | Analysis scripts | Ready | Hardware pending | Labs | Build the AD9361 RX gain/overload table from the clean-image baseline. |
| 07 | TX/RX chains | Ready | Executable | DUC/DDC demos | Ready | Hardware pending | Labs | Add RF loopback measurement package. |
| 08 | Modulation and synchronization | Ready | Executable | Synchronization demos | Ready | Optional | Sync CI | Add impairment sweeps and BER/EVM dashboards. |
| 09 | Recording and analysis tools | Ready | Executable | IQ readers | Ready | Hardware pending | Recording CI | Update QPSK dataset manifest with real checksum or synthetic generator. |
| 10 | KiCad and basic electronics | Ready | Draft | Calculators / templates | Partial | Bench pending | Docs | Add measured breadboard photos and KiCad exports. |
| 11 | Integrated SDR project | Ready | Executable | Simulation package + BPSK reference package + AXI-Lite helper + gpreg overlay tooling + historical `done+timeout` bring-up evidence + overlap contention probe + raw-clean-boot proof that the `bridge_txrx_mux` candidate reaches PL and exposes `axi_gpreg` at `0x79040000` even though AD9361 still times out, plus manual-UART `fpga load` evidence that the stock BOOT partition is the only currently boot-safe external PL payload | Ready | Hardware pending | Labs | Reproduce the stock partition's boot-safe properties in a source-correlated or editable shell, then resume RF discovery for the first non-zero `RECEIVED_BITS`. |
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
| `datasets/lab1_0_rtl_sdr_observation/` | Real passive RTL-SDR air captures from the first SDR++ bring-up session, stored as WAV IQ files through Git LFS with manifests, SHA256 checksums, capture settings and replay commands. |
| `hardware/7020_ad936x_sdr/boot/course_clean/autorun.sh` | Clean stock-image management overlay with fixed `eth0`, DHCP, and safe TX defaults. |
| `hardware/7020_ad936x_sdr/boot/course_clean/uEnv_course_bpsk_overlay.txt` | Boot-time U-Boot overlay that loads the course PL image and removes stale Linux PL nodes before `bootm`. |
| `hardware/7020_ad936x_sdr/boot/extract_stock_system_top_partition.py` | Reproducible extractor for the only externally loaded boot-safe `system_top.bit` partition payload currently known: the one embedded in `boot/sd_image/BOOT.bin`. |
| `hardware/7020_ad936x_sdr/boot/build_system_bit_bin.py` | Reproducible converter from raw Xilinx `.bit` to the word-swapped `.bit.bin` payload accepted by the board's manual U-Boot `fpga load` path. |
| `hardware/7020_ad936x_sdr/boot/validate_manual_uart_fpga_load.py` | Reproducible helper that stops autoboot over UART, runs manual `fpga load`, boots Linux, and tells whether a `.bit.bin` payload really survived as an externally loaded PL image. |
| `hardware/7020_ad936x_sdr/compare_fpga_payloads.py` | Normalizes raw `.bit` inputs to the manual `fpga load` payload format and reports first-diff offsets versus stock or course candidates. |
| `hardware/7020_ad936x_sdr/rebuild_vendor_xpr_snapshot_mio_patch.tcl` | Disposable Vivado rebuild flow that patches only `sys_ps7` MIO14/15 on the saved vendor `zc702.xpr` snapshot before synth/impl/export. |
| `docs/assets/lab112_clean_boot_pl_validation.json` | Persistent evidence that raw `.bit` `fpga loadb` proves arbitrary PL replacement but still breaks AD9361 for every non-stock candidate tried, while manual `.bit.bin` `fpga load` currently clean-boots only the extracted stock BOOT partition payload. |
| `docs/assets/stock_vs_vendor_reference_fpga_payload_diff.json` | First-diff evidence showing where the extracted stock BOOT payload diverges from the source-correlated vendor-reference fpga-load payload. |
| `docs/assets/stock_vs_bridge_txrx_mux_fpga_payload_diff.json` | First-diff evidence showing where the extracted stock BOOT payload diverges from the corrected course `bridge_txrx_mux` fpga-load payload. |
| `docs/assets/vendor_reference_vs_vendor_xpr_mio14_15_payload_diff.json` | Normalized payload diff proving that the MIO14/15-patched editable vendor snapshot matches the source-correlated vendor reference byte-for-byte on the manual `fpga load` path. |
| `docs/assets/lab118_axi_gpreg_bringup_cleanboot_raw.json` | Direct raw-clean-boot gpreg readback for the `bridge_txrx_mux` candidate: PL reached fabric, ID/signature matched, `tx_valid_count` incremented, and `rx_valid_count` stayed zero. |
| `hardware/7020_ad936x_sdr/ps/ad936x_no_os_reference/platform/hw/system_top.bit` | Source-correlated vendor reference bitstream that still proves raw `fpga loadb` reaches PL, but still does not keep AD9361 alive on this board. |
| `hardware/7020_ad936x_sdr/compare_xsa_handoffs.py` | Source-level XSA/HWH drift detector for rebuilt shells versus the vendor reference handoff. |
| `docs/assets/vendor_reference_vs_vendor_only_handoff_diff.json` | Persistent diff showing that the normalized pure-Tcl `vendor_only` rebuild still diverges only at `sys_ps7.PCW_S_AXI_HP0_FREQMHZ`, DMA protocol selection, and `axi_ad9361.SPEED_GRADE`. |
| `docs/assets/vendor_reference_vs_bridge_rx_only_handoff_diff.json` | Persistent diff showing what the intermediate `bridge_rx_only` overlay adds on top of the still-not-boot-safe vendor shell. |
| `docs/assets/vendor_reference_vs_vendor_xpr_snapshot_handoff_diff.json` | Persistent diff showing the historical unpatched `zc702.xpr` snapshot drift against the vendor reference XSA at `sys_ps7` MIO14/15 direction fields. |
| `docs/assets/vendor_reference_vs_vendor_xpr_mio14_15_patch_handoff_diff.json` | Persistent diff showing that the MIO14/15-patched vendor `zc702.xpr` snapshot rebuild reaches zero module/memrange/parameter drift against the vendor reference XSA. |
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
- Block 1 already includes real passive RTL-SDR air recordings captured in SDR++ and stored through Git LFS with manifests and reproducibility metadata.

## Main gaps to close

1. Replace the QPSK manifest-only dataset with a validated small file or external link.
2. Add board-level measurements for the Zynq/AD9363 path.
3. Promote Block 5 OOC FPGA reports to placed-and-routed top-level design data.
4. Keep RU/EN pages aligned when adding new labs.
5. Turn one QPSK or tone flow into a complete final report with plots and limitations.
6. Review the publication/legal status of real off-air captures before treating them as public redistributable course data.

## Priority improvements

1. Promote one complete `Model -> FPGA -> RF -> Measurement` demo to portfolio-ready status.
2. Add a publication-cleared small QPSK IQ dataset or synthetic generator for recording and replay labs.
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
