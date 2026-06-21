# Lab Index

This page provides a compact index of the executable and report-oriented labs in the course.

## Legend

| Mark | Meaning |
|---|---|
| Python | executable Python model or analyzer |
| MATLAB | MATLAB/Simulink-oriented task or planned translation |
| Verilog | RTL or testbench activity |
| Report | documentation/checklist/report deliverable |
| CI | covered by a GitHub Actions workflow or representative smoke path |

## Labs

| Lab | Block | Topic | Python | Verilog | Report | CI | Main metrics / artifacts |
|---|---|---|---:|---:|---:|---:|---|
| 2.1 | Signals and sampling | Sampling axis and interpretation | yes | no | yes | yes | time plot, correct/wrong FFT axis, interpretation error |
| 2.2 | Signals and sampling | Aliasing sweep | yes | no | yes | yes | alias map, example spectra, alias error |
| 2.3 | Signals and sampling | I/Q interpretation and mirroring | yes | no | yes | yes | complex vs real spectra, swapped-IQ mirror check |
| 3.1 | DSP basics | FFT windows and leakage | yes | no | yes | partial | spectra, leakage comparison |
| 3.2 | DSP basics | FIR low-pass filter | yes | no | yes | partial | FIR response, filtered spectrum |
| 3.3 | DSP basics | Digital mixing | yes | planned link | yes | partial | spectra before/after mixing |
| 3.4 | DSP basics | Decimation | yes | no | yes | partial | anti-aliasing, decimated spectrum |
| 4.1 | Fixed-point | Fixed-point FIR | yes | bridge | yes | partial | quantization error, fixed-point formats |
| 4.2 | Fixed-point | Fixed-point digital mixer | yes | bridge | yes | partial | mixer error, NCO precision |
| 5.1 | HDL flow | Streaming interface and testbench | no | yes | yes | yes | VCD, PASS/FAIL |
| 5.2 | HDL flow | FIR RTL mapping | yes vectors | yes | yes | yes | vector match, saturation, latency |
| 5.3 | HDL flow | NCO mixer RTL | yes vectors | yes | yes | yes | vector match, complex multiply |
| 5.4 | HDL flow | AXI-Stream wrapper | no | yes | yes | yes | handshake, backpressure, tlast |
| 5.5 | HDL flow | Float vs fixed vs RTL comparison | yes | reuse vectors | yes | partial | RMSE/max error, resource-latency table |
| 5.6 | HDL flow | BPSK RRC TX FIR RTL | yes vectors | yes | yes | yes | pulse-shaped sample match, Q1.15 FIR, coefficient handoff |
| 5.7 | HDL flow | BPSK 8x symbol upsampler | yes vectors | yes | yes | yes | zero-stuff expansion, symbol/sample bridge |
| 5.8 | HDL flow | BPSK RX matched filter and bit recovery | yes vectors | yes | yes | yes | deterministic bit recovery, payload BER |
| 5.9 | HDL flow | BPSK framed TX/RX loopback top-level | yes vectors | yes | yes | yes | framed burst, flush tail, zero-error loopback |
| 5.10 | HDL flow | Zynq-ready BPSK BER top-level | yes vectors | yes | yes | yes | start/busy/done, BER counters, TX/RX sample seam |
| 5.11 | HDL flow | AXI-Lite control wrapper for the BPSK BER top-level | yes vectors | yes | yes | yes | register map, start polling, BER readback |
| 6.1 | RF frontend | RF frequency plan | yes/report | no | yes | partial | expected offset, frequency error |
| 6.2 | RF frontend | Gain staging and overload | yes/report | no | yes | partial | clipping, SNR, SFDR notes |
| 6.3 | RF frontend | AD9363 settings and iio_attr | no | no | yes | manual | settings table, metadata |
| 6.4 | RF frontend | Synthetic RF capture analysis | yes | no | yes | yes | FFT, SNR, clipping, metrics JSON |
| 6.5 | RF frontend | RF impairment calibration | yes | no | yes | partial | DC/IQ/image/LO metrics before/after |
| 6.6 | RF frontend | Clean-image Zynq RX-only observation | yes | no | yes | manual | CI16 capture, manifest, offline FFT, Zynq-vs-RTL overlay |
| 7.1 | TX/RX | TX/RX chain architecture | no | no | yes | manual | architecture, sample-rate plan |
| 7.2 | TX/RX | DUC/DDC frequency translation | yes | no | yes | yes | spectra, residual frequency error |
| 7.3 | TX/RX | Loopback metrics | yes | no | yes | yes | constellation, EVM, SNR, BER |
| 7.4 | TX/RX | Packet receiver detection | yes | no | yes | partial | TP/FP/miss, detection probability, timing error |
| 8.1 | Synchronization | CFO estimation/correction | yes | no | yes | yes | CFO error, EVM, BER |
| 8.2 | Synchronization | Phase offset correction | yes | no | yes | yes | phase error, EVM, BER |
| 8.3 | Synchronization | Timing recovery | yes | no | yes | yes | timing phase, eye preview, EVM/BER |
| 8.4 | Synchronization | End-to-end sync chain | yes | no | yes | yes | CFO, phase, timing, EVM/BER |
| 8.5 | Synchronization | OFDM mini link | yes | no | yes | partial | sync metric, CFO estimate, channel estimate, BER/EVM |
| 8.6 | Synchronization | Channel coding BER comparison | yes | no | yes | partial | BER vs SNR, coding and interleaving gain |
| 9.1 | IQ recording | IQ file format and metadata | no | no | yes | manual | metadata completeness |
| 9.2 | IQ recording | CI16 IQ reader and analyzer | yes | no | yes | yes | FFT, peak, SNR, DC, clipping |
| 9.3 | IQ recording | Multi-format IQ reader | yes | no | yes | yes | CI16/CU8/CF32 spectra, metrics JSON |
| 10.1 | Electronics | Passive RC filter | no | no | yes | manual | cutoff calculation, schematic |
| 10.2 | Electronics | Attenuator pad | no | no | yes | manual | attenuation, safety notes |
| 10.3 | Electronics | RF measurement safety checklist | no | no | yes | manual | safety checklist |
| 10.4 | Electronics | KiCad schematic mini-project | no | no | yes | manual | schematic concept, BOM |
| 11.1 | Integrated project | Requirements and architecture | no | no | yes | manual | requirements, architecture |
| 11.2 | Integrated project | End-to-end simulation package | yes/reuse | no | yes | manual | figures, metrics JSON |
| 11.3 | Integrated project | FPGA/RF integration checklist | no | yes/reuse | yes | manual | testbench, RF checklist |
| 11.4 | Integrated project | Final measurement report | no | no | yes | manual | pass/fail table, report |
| 11.5 | Integrated project | AXI DMA latency and jitter | yes | no | yes | partial | latency trace, histogram, p95/p99, throughput |
| 11.6 | Integrated project | Measurement uncertainty budget | yes | no | yes | partial | Type A/B contributions, expanded uncertainty |
| 11.7 | Integrated project | PS-side AXI-Lite BPSK bring-up | yes | yes/reuse | yes | yes | ID readback, busy/done polling, BER counter JSON |
| 11.8 | Integrated project | AD9361 gpreg BPSK overlay | yes | yes/reuse | yes | manual | CLG400 overlay, gpreg ID/signature evidence, stock-shell clean-boot baseline |
| 11.9 | Integrated project | AD9361 RF discovery sweep | yes | yes/reuse | yes | manual | gated sweep plan to resume after sample-path reintegration around the stock shell |
| 11.10 | Integrated project | Timed IIO burst capture | yes | yes/reuse | yes | manual | timed CI16 snapshot, trigger-relative power metrics, RF-vs-digital evidence |
| 11.11 | Integrated project | IIO vs gpreg contention probe | yes | yes/reuse | yes | manual | standalone-vs-overlap matrix, DMAC snapshots, contention evidence |

## Recommended assessment path

1. Run `python tools/tasks.py labs`.
2. Run `python tools/tasks.py hdl` if Icarus Verilog is installed.
3. Review generated artifacts in `docs/assets`.
4. Fill the lab report template from `templates/lab_report.template.md`.
5. Use Block 11 to combine selected results into a final project.
