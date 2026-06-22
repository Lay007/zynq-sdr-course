# Python Scripts and Automation

## Purpose
This folder is intended for reproducible processing scripts, measurement automation, and quick hypothesis checks for Block 11 “Integrated SDR Project”.

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

## Quality criteria
- files should be reproducible and understandable without oral explanation;
- experiment parameters, tool versions, and limits should be documented next to the material;
- the materials should help the student reach at least one outcome of the block: project architecture diagram, interface table.
