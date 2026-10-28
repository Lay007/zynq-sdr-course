# Getting Started

This is the shortest practical route from a fresh workstation to a reproducible SDR course result. For the full lesson sequence, follow the [Student path](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/student-path.md).

## 1. Choose a route before installing hardware tools

| Route | Equipment | First outcome |
| --- | --- | --- |
| Laptop only | Python, optional MATLAB/Simulink | DSP plots, fixed-point models, software checks |
| RTL-SDR observation | Laptop + RTL-SDR | Receive/capture IQ and inspect its spectrum |
| FPGA/SDR board | Zynq-7020 + AD936x | RTL bring-up, PS/PL control and controlled RF experiments |
| Measurement bench | Board + attenuators and instruments | Calibrated or explicitly qualified hardware measurements |

The exact prerequisites are in [Learning routes](https://github.com/Lay007/zynq-sdr-course/blob/main/LAB_TRACK_en.md). MATLAB/Simulink is valuable for the model-to-hardware workflow but is not required for every Python lab.

## 2. Run the software baseline

Use Python **3.12 or newer**. From a terminal:

```bash
git clone https://github.com/Lay007/zynq-sdr-course.git
cd zynq-sdr-course
python tools/tasks.py install
python tools/tasks.py docs
python tools/tasks.py labs
```

Expected baseline: the strict MkDocs build completes, and the representative lab suite reports PASS. Inspect the named failure and its log rather than assuming that a partially completed run passed.

For the broader checks:

```bash
python tools/tasks.py smoke
```

The HDL suite additionally requires Icarus Verilog (`iverilog` and `vvp`) on PATH. For local development checks, see [Reproducibility guide](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/reproducibility-guide.md) and [CI matrix](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/ci-matrix.md).

## 3. Add tools only when the next lab needs them

- **Icarus Verilog 12:** self-checking HDL testbenches, including Block 5.
- **MATLAB/Simulink:** optional reference and fixed-point models.
- **Vivado 2021.1:** the board-specific course implementation and reports; not needed for basic DSP exercises.
- **Git LFS:** download large recorded IQ payloads referenced by the repository.

```bash
git lfs install
git lfs pull
```

If a supposed recording contains just a short text pointer, fetch the LFS content before debugging the IQ decoder.

## 4. Verify one small result

Start with one DSP lab and record:

1. The command and software versions used.
2. The generated plot or metrics file.
3. The parameters (sample rate, FFT length, fixed-point format if applicable).
4. One sentence describing what was demonstrated.

Before a physical RF experiment, read the [Hardware checklist](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/hardware-checklist.md) and [RF safety guide](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/rf-safety.md).

## Where to go next

[Hardware](Hardware) · [DSP to FPGA](DSP-to-FPGA) · [Troubleshooting](Troubleshooting) · [Lab index](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/lab-index.md)
