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
| 6.1 | RF frontend | RF frequency plan | yes/report | no | yes | partial | expected offset, frequency error |
| 6.2 | RF frontend | Gain staging and overload | yes/report | no | yes | partial | clipping, SNR, SFDR notes |
| 6.3 | RF frontend | AD9363 settings and iio_attr | no | no | yes | manual | settings table, metadata |
| 6.4 | RF frontend | Synthetic RF capture analysis | yes | no | yes | yes | FFT, SNR, clipping, metrics JSON |
| 7.1 | TX/RX | TX/RX chain architecture | no | no | yes | manual | architecture, sample-rate plan |
| 7.2 | TX/RX | DUC/DDC frequency translation | yes | no | yes | yes | spectra, residual frequency error |
| 7.3 | TX/RX | Loopback metrics | yes | no | yes | yes | constellation, EVM, SNR, BER |
| 8.1 | Synchronization | CFO estimation/correction | yes | no | yes | yes | CFO error, EVM, BER |
| 8.2 | Synchronization | Phase offset correction | yes | no | yes | yes | phase error, EVM, BER |
| 8.3 | Synchronization | Timing recovery | yes | no | yes | yes | timing phase, eye preview, EVM/BER |
| 8.4 | Synchronization | End-to-end sync chain | yes | no | yes | yes | CFO, phase, timing, EVM/BER |
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

## Recommended assessment path

1. Run `make labs`.
2. Run `make hdl` if Icarus Verilog is installed.
3. Review generated artifacts in `docs/assets`.
4. Fill the lab report template from `templates/lab_report.template.md`.
5. Use Block 11 to combine selected results into a final project.
