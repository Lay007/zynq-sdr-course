# Dual-modem Zynq SDR final implementation report

## Objective and acceptance criteria

The project connects the BPSK/QPSK reference paths, the course RTL, the Zynq/AD9361 integration design and the current hardware evidence. The implementation portion is accepted when the canonical HDL suite passes, the exact integrated top-level is fully routed and all constrained timing endpoints pass.

Board-level acceptance is stricter: BPSK and QPSK must also pass a repeatable clean-boot series, followed by a manifest-backed external RF measurement. Those gates are still open and are not inferred from Vivado success.

## Architecture

```text
reference vectors -> BPSK/QPSK RTL -> dual-modem gpreg bridge
                                      |
                                      v
PS7 + AXI + AD9361 interface -> placed-and-routed XC7Z020 design -> local bitstream
                                      |
                                      v
                         runtime board helpers -> BER / capture evidence
```

## Evidence summary

| Layer | Evidence | Result | Qualification |
|---|---|---|---|
| Reference/model | BPSK package and deterministic QPSK replay | reproducible vectors, plots and metrics | synthetic |
| RTL | canonical HDL smoke suite | 18/18 tests pass; BPSK/QPSK BER=0 in their deterministic tests | simulation |
| QPSK bridge | dual-modem loopback testbench | 140 symbols / 280 bits, BER=0 | simulation |
| FPGA implementation | integrated Vivado 2021.1 reports | fully routed; timing met | implementation |
| BPSK board path | promoted on-chip PL result | 281 compared bits, BER=0 | measured single promoted result |
| QPSK board path | Lab 11.27 helper | executable offset/retry and repeatability workflow | hardware pending |
| External RF | RTL-SDR/Zynq capture workflows | tone and monitor paths exist | complete dual-modem proof pending |

## Integrated implementation result

The current dual-modem top-level was synthesized, placed, routed and written as a bitstream for `xc7z020clg400-2` with Vivado 2021.1.

| Metric | Result |
|---|---:|
| LUT | 13,795 |
| FF | 21,780 |
| DSP | 28 |
| BRAM tiles | 4.0 |
| WNS | 0.354 ns |
| TNS | 0.000 ns |
| Failing / total endpoints | 0 / 48,851 |
| Fully routed / routable nets | 29,899 / 29,899 |
| Routing errors | 0 |

The generated bitstream is 2,118,912 bytes. It is not committed; the promoted metrics record SHA256 `5e46cf4e23b5485aef759822a8deef541383ed8eba5171d24728a36f9cdd1b8d` so a local artifact can be checked against this run.

## Reproduction

Run software and RTL checks:

```bash
python -m pytest -q
python tools/run_block5_hdl_smoke.py --no-generate
python tools/check_dataset_manifests.py
mkdocs build --strict
```

On Windows with Vivado 2021.1 installed, rebuild the integrated implementation and promote normalized reports:

```powershell
python tools/generate_integrated_vivado_reports.py --build
```

To reparse a completed local implementation without rebuilding:

```powershell
python tools/generate_integrated_vivado_reports.py
```

Primary artifacts:

- `reports/fpga/integrated-zynq-implementation-summary.md`
- `reports/fpga/integrated_zynq_raw/integrated_zynq_metrics.json`
- `reports/fpga/integrated_zynq_raw/system_top_timing_summary_routed.rpt`
- `reports/fpga/integrated_zynq_raw/system_top_utilization_placed.rpt`
- `reports/fpga/integrated_zynq_raw/system_top_route_status.rpt`

## Engineering conclusion

The course dual-modem PL design fits the target XC7Z020, is fully routed and closes timing with positive setup margin. This removes FPGA implementation feasibility as the immediate blocker.

It does not prove that AD9361 state survives reload correctly, that BPSK/QPSK starts reliably from a clean boot, or that the RF link meets BER/EVM limits. The next decisive experiment is a controlled clean-boot series using Lab 11.27, followed by a cabled or carefully attenuated external capture with configuration metadata, BER, EVM, SNR and uncertainty notes.
