# DSP foundation track

This page strengthens the DSP depth of the course without changing the repository into a notebook-first project. The goal is to make the SDR path more rigorous: every spectral, filtering and multirate topic should have an engineering consequence for fixed-point code, HDL and FPGA implementation.

## Purpose

The course route is extended with a compact DSP backbone:

```text
FFT complexity -> convolution / correlation -> windows -> resampling -> CIC -> fixed-point -> FPGA bridge
```

This track sits between the early signal theory blocks and the hardware-oriented Zynq/AD9363 work.

## Why these topics matter

| Topic | SDR meaning | Fixed-point / FPGA meaning |
|---|---|---|
| FFT complexity | Spectrum display, frequency planning, measurement reports. | Defines whether full-spectrum FFT, selected-bin detection or streaming architecture is appropriate. |
| Convolution | FIR filtering, channel response and pulse shaping. | Maps to multiply-accumulate, symmetric FIR optimization and latency/resource trade-offs. |
| Correlation | Preamble search, delay estimation, synchronization and matched filtering. | Maps to sliding correlators, matched filters, accumulator width and threshold logic. |
| Windows | Leakage control and weak-signal detection near strong components. | Maps to coefficient quantization, ROM tables and deterministic spectral test vectors. |
| Resampling | Sample-rate planning between RF, baseband and analysis tools. | Requires anti-alias filters, interpolation/decimation staging and clock-rate budgeting. |
| CIC | Efficient high-rate decimation/interpolation without multipliers. | Uses integrators, combs, delays, bit growth analysis and optional droop compensation. |

## Placement in the course

| Course block | Added DSP depth |
|---|---|
| Block 02 — Signals and sampling | Explicit aliasing, sample-rate and bandwidth constraints. |
| Block 03 — DSP basics | FFT complexity, convolution/correlation and windows. |
| Block 04 — Simulink and fixed-point | Scaling, quantization and bit-growth experiments. |
| Block 05 — FPGA / HDL flow | RTL-friendly structures, latency and resource estimates. |
| Block 07 — TX/RX chains | Resampling, DDC/DUC staging and CIC decimation. |
| Block 08 — Synchronization | Correlation-based detection and metric-driven validation. |
| Block 09 — Recording and analysis | Spectrum quality, frequency-axis correctness and IQ metadata. |

## Required engineering outputs

Every topic in this track should eventually produce:

- one concise theory page;
- one deterministic script, not a notebook dependency;
- one or more generated figures in `docs/assets`;
- one metrics JSON file;
- a fixed-point or FPGA implication table;
- expected values suitable for CI checks;
- links from the relevant RU/EN lab pages.

## FFT complexity target

The FFT section should compare:

| Method | Useful when | Engineering lesson |
|---|---|---|
| Direct DFT | Very small vectors, teaching, exact reference. | Simple but scales poorly. |
| FFT | Full-spectrum analysis and measurement dashboards. | Efficient but needs memory, ordering and streaming decisions. |
| Goertzel / selected-bin detection | A few known tones or narrowband checks. | May be better than full FFT when only a few bins are needed. |

Expected future artifact names:

```text
docs/assets/lab35_dft_fft_complexity.png
docs/assets/lab35_selected_bin_tradeoff.png
docs/assets/lab35_fft_complexity_metrics.json
```

## Convolution and correlation target

The course should explicitly separate:

- convolution for filtering;
- correlation for detection and synchronization;
- FFT convolution for long filters and block processing;
- matched filtering for known preambles.

Expected future artifact names:

```text
docs/assets/lab36_convolution_filtering.png
docs/assets/lab36_correlation_detection.png
docs/assets/lab36_correlation_metrics.json
```

## Windowing target

Windowing should be taught as an engineering trade-off rather than a decorative FFT option.

| Window property | Measurement consequence |
|---|---|
| Main-lobe width | Frequency resolution and tone separation. |
| Side-lobe level | Ability to see weak signals near strong signals. |
| Coherent gain | Correct amplitude interpretation. |
| Equivalent noise bandwidth | Noise-floor interpretation. |

Expected future artifact names:

```text
docs/assets/lab37_window_tradeoffs.png
docs/assets/lab37_weak_signal_detection.png
docs/assets/lab37_window_metrics.json
```

## Resampling and CIC target

The multirate section should lead toward a practical SDR receiver chain:

```text
high-rate ADC / RF frontend -> CIC decimator -> compensation FIR -> channel filter -> demodulator
```

The key bridge is that CIC filters are not just another filter type. They are a hardware-friendly multirate structure with adders, subtractors and delay lines instead of multipliers.

Expected current/future artifact names:

```text
docs/assets/lab75_cic_response.png
docs/assets/lab75_cic_decimation_time.png
docs/assets/lab75_cic_bit_growth.png
docs/assets/lab75_cic_metrics.json
```

## Acceptance criteria for this track

The DSP foundation track becomes mature when:

- FFT complexity is represented by deterministic plots and metrics;
- convolution and correlation are separated in theory and lab tasks;
- windows are connected to weak-signal detection;
- resampling is connected to anti-alias filtering and SDR rate planning;
- CIC is connected to bit growth, fixed-point arithmetic and FPGA architecture;
- at least one executable lab is part of `tools/run_all_labs.py`.

## References for the engineering direction

- DSP tasks include filtering, spectral analysis and signal detection; these are the backbone of SDR labs and measurement workflows.
- CIC filters are attractive for FPGA-style multirate processing because they can be implemented with delays, additions and subtractions rather than multipliers.
- FFT-based analysis is efficient for full-spectrum work, while selected-bin methods can be appropriate when only a small number of known frequencies must be detected.
