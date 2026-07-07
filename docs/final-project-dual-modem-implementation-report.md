# Dual-modem Zynq SDR final implementation report

## Objective and acceptance criteria

The project connects the BPSK/QPSK reference paths, the course RTL, the Zynq/AD9361 integration design and the current hardware evidence. The implementation portion is accepted when the canonical HDL suite passes, the exact integrated top-level is fully routed and all constrained timing endpoints pass.

Board-level acceptance is stricter: repeatable silicon operation and a manifest-backed external RF measurement are separate gates. The timing-clean QPSK fabric-loopback payload is repeatable, and the promoted external RTL-SDR session reaches BER=0 across 30/30 bursts and 8,400 compared bits.

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
| FPGA implementation | two integrated Vivado 2021.1 flows | hardware-working snapshot is fully routed and timing-clean | internal-path signoff candidate |
| BPSK board path | promoted on-chip PL result | 281 compared bits, BER=0 | measured single promoted result |
| QPSK board path | Lab 11.27 fabric loopback | timing-clean payload: 4/4 boots, 13/13 attempts at BER=0 for 280 bits | measured silicon |
| External RF | Lab 11.28 RTL-SDR OTA QPSK | 30/30 bursts, 0/8,400 bit errors, median EVM 21.32%, median CFO +1.964 kHz | measured session |

## Integrated implementation result

The dual-modem top-level was synthesized through two flows for `xc7z020clg400-2` with Vivado 2021.1. The standalone reconstruction remains useful diagnostically; the vendor snapshot is the hardware-correlated signoff candidate.

| Metric | Standalone recreated | Vendor snapshot |
|---|---:|---:|
| LUT | 13,795 | 27,597 |
| FF | 21,780 | 36,169 |
| DSP | 28 | 216 |
| BRAM tiles | 4.0 | 8.0 |
| WNS | +0.354 ns | +0.003 ns |
| TNS | 0.000 ns | 0.000 ns |
| Failing endpoints | 0 | 0 |
| Routing errors | 0 | 0 |

The standalone bitstream is timing-clean but produced zero TX/RX valid counts after runtime reload. The vendor-snapshot payload closes timing after the RX channel-select CDC fix and passes QPSK fabric BER on the same generated payload. The remaining caveat is the `+0.003 ns` WNS margin, which should be challenged with repeat builds or a seed sweep.

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
- `reports/hardware/qpsk-rtl-sdr-qualification-20260707.md`

## Engineering conclusion

The QPSK modem is proven on the real Zynq PL at BER=0. The final timing-clean payload is repeatable across four boot sessions and 13 attempts, and FPGA timing/board correlation is closed for the internal fabric path.

The next FPGA task is to improve and demonstrate timing margin across repeat builds. The next measurement task is independent-session RTL-SDR QPSK statistics and a controlled cabled comparison; 0/8,400 bits bounds the tested session but does not establish a long-duration BER floor.
