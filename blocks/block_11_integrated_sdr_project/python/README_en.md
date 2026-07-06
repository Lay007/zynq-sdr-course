# Python Scripts and Automation

## Purpose
This folder is intended for reproducible processing scripts, measurement automation, and quick hypothesis checks for Block 11 “Integrated SDR Project”.

## Bench connection defaults

Hardware helpers read `ZYNQ_SSH_HOST`, `ZYNQ_SSH_USER`, `ZYNQ_SSH_PASSWORD`, `ZYNQ_SSH_PORT`, `ZYNQ_SSH_TIMEOUT_S` and `ZYNQ_IIO_URI`. If unset, they retain the vendor-image defaults (`192.168.40.1`, `root`, `analog`). Set environment variables instead of placing non-default credentials in scripts or command history.

## What should be stored here
- materials that directly support the block topics: integrated-project decomposition; signal and interface architecture; combining DSP, RF, and control logic;
- files that can be reused in a laboratory task, demonstration, or mini-project;
- short notes describing how to run the material, where the data comes from, and what result is expected.

## Minimum meaningful content
- one reproducible example for a key idea of the block;
- one artifact or artifact set suitable for insertion into a report;
- one note that connects the folder contents with the engineering logic of the course.

## Suggested file names
- `integration_analysis.py`
- `system_test_sweep.py`
- `architecture_visualization.py`

## Current notable helpers
- `lab_11_12_runtime_fpga_manager_reload.py`: hot-loads a checked `.bit.bin` payload and re-probes `axi_gpreg` plus IIO visibility.
- `lab_11_13_stock_vs_runtime_rx_compare.py`: proves the stock-shell RX baseline first, then shows what breaks after the runtime overlay reload.
- `lab_11_14_stock_shell_bpsk_ota.py`: uses the stock AD9361 Linux shell as a host-driven OTA BPSK fallback while the PL overlay RX path is still blocked.
- `lab_11_20_read_rtl_wav_ota_bpsk_ber.py`: reads a stereo RTL-SDR/SDR++ WAV IQ capture, searches the residual carrier offset, resamples to the reference BPSK rate when needed, and reports BER/EVM against either the stock-shell Lab 11.14 waveform or the shared runtime `end_to_end_bpsk_reference` package.
- `lab_11_21_capture_rtl_sdr_monitor_wav.py`: keys the stock-shell AD9361 BPSK TX path on ZynqSDR, captures a fresh monitor WAV IQ through RTL-SDR, and writes a manifest that can be fed directly into `lab_11_20_read_rtl_wav_ota_bpsk_ber.py`.
- `lab_11_22_capture_runtime_pl_rtl_monitor_wav.py`: hot-loads the runtime `bridge_txrx_mux` overlay, configures AD9361, records a fresh RTL-SDR monitor WAV around repeated PL-owned BPSK start pulses, and writes a manifest for offline BER replay of the runtime/PL path.
- `lab_11_23_runtime_pl_rtl_monitor_sweep.py`: runs a focused runtime/PL external-monitor sweep around the known live point, ranks the tested parameter sets by offline RTL-SDR BER, and can rerun the best point as canonical evidence.
- `lab_11_24_capture_dds_tone_rtl_monitor_wav.py`: captures a controlled external RTL-SDR WAV around a Zynq DDS tone in either `stock` or `runtime` mode and writes a manifest for immediate replay through the Block 9 WAV IQ analyzer.

## Quality criteria
- files should be reproducible and understandable without oral explanation;
- experiment parameters, tool versions, and limits should be documented next to the material;
- the materials should help the student reach at least one outcome of the block: project architecture diagram, interface table.
