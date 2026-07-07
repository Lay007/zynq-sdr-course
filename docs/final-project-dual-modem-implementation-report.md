# Dual-modem Zynq SDR final implementation report

## Objective and acceptance criteria

The project connects the BPSK/QPSK reference paths, the course RTL, the Zynq/AD9361 integration design and the current hardware evidence. The implementation portion is accepted when the canonical HDL suite passes, the exact integrated top-level is fully routed and all constrained timing endpoints pass.

Board-level acceptance is stricter: repeatable silicon operation and a manifest-backed external RF measurement are separate gates. QPSK fabric-loopback repeatability is now measured; RF and combined timing/board signoff remain open.

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
| FPGA implementation | two integrated Vivado 2021.1 flows | standalone timing passes; hardware-working snapshot timing fails | signoff pending |
| BPSK board path | promoted on-chip PL result | 281 compared bits, BER=0 | measured single promoted result |
| QPSK board path | Lab 11.27 fabric loopback | 5/5 boots, 14/14 attempts at BER=0 for 280 bits | measured silicon |
| External RF | RTL-SDR/Zynq capture workflows | tone and monitor paths exist | complete dual-modem proof pending |

## Integrated implementation result

The dual-modem top-level was synthesized through two flows for `xc7z020clg400-2` with Vivado 2021.1. The results expose a correlation defect rather than a final signoff point.

| Metric | Standalone recreated | Vendor snapshot |
|---|---:|---:|
| LUT | 13,795 | 27,887 |
| FF | 21,780 | 36,203 |
| DSP | 28 | 212 |
| BRAM tiles | 4.0 | 8.0 |
| WNS | +0.354 ns | -1.676 ns |
| TNS | 0.000 ns | -53.405 ns |
| Failing endpoints | 0 | 66 |
| Routing errors | 0 | 0 |

The standalone bitstream is timing-clean but produced zero TX/RX valid counts after runtime reload. The vendor-snapshot payload is hardware-correlated and passes QPSK fabric BER, but fails timing. Neither result alone satisfies final acceptance.

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
python tools/generate_integrated_vivado_reports.py --flow standalone --build
python tools/generate_integrated_vivado_reports.py --flow snapshot --build
```

To reparse a completed local implementation without rebuilding:

```powershell
python tools/generate_integrated_vivado_reports.py --flow standalone
python tools/generate_integrated_vivado_reports.py --flow snapshot
```

Primary artifacts:

- `reports/fpga/integrated-zynq-implementation-summary.md`
- `reports/fpga/integrated_zynq_raw/integrated_zynq_metrics.json`
- `reports/fpga/integrated_zynq_raw/system_top_timing_summary_routed.rpt`
- `reports/fpga/integrated_zynq_raw/system_top_utilization_placed.rpt`
- `reports/fpga/integrated_zynq_raw/system_top_route_status.rpt`
- `reports/fpga/integrated-zynq-snapshot-implementation-summary.md`
- `reports/fpga/integrated_zynq_snapshot_raw/integrated_zynq_metrics.json`
- `reports/hardware/qpsk-fabric-loopback-qualification-20260707.md`

## Engineering conclusion

The QPSK modem is proven on the real Zynq PL at BER=0 and is repeatable across five boot sessions. FPGA capacity and routing are feasible, but final timing/board correlation is not closed.

The next FPGA task is to make the hardware-correlated snapshot meet timing or restore sample clocks in the timing-clean standalone flow. The next measurement task is an external RTL-SDR QPSK capture with configuration metadata, BER, EVM, SNR and uncertainty notes.
