# Contributing course labs

This guide defines the expected structure for new labs in the Zynq SDR Course. It keeps Russian and English pages aligned and makes every lab reproducible, measurable and useful as an engineering artifact.

## Lab design principle

A good lab should answer three questions:

1. What engineering concept is being validated?
2. What model, script, hardware setup or measurement proves it?
3. What result should the learner compare against?

## Required lab structure

Every new lab page should contain:

| Section | Purpose |
|---|---|
| Goal | One clear engineering objective. |
| Background | Short theory needed for the task. |
| Inputs | Parameters, files, scripts, hardware and assumptions. |
| Procedure | Step-by-step reproducible workflow. |
| Expected result | Plots, metrics, console output or measurement observations. |
| Validation | How to know the result is correct. |
| Troubleshooting | Common failure modes and fixes. |
| Report checklist | What the learner must include in the lab report. |
| Safety notes | Required for RF, power, soldering or measurement hardware. |

## Required artifacts by lab type

| Lab type | Minimum artifacts |
|---|---|
| Theory-only | Markdown page, equations, diagrams, references. |
| Python DSP | Python script or notebook-friendly script, generated figure, expected numerical result. |
| MATLAB / Simulink | MATLAB script or model description, reference parameters, exported plots or screenshots. |
| C++ DSP | Source file, build/run command, test vector or expected output. |
| Verilog / FPGA | RTL module, testbench, command line simulation path, expected waveform or console result. |
| RF / SDR hardware | RF path diagram, safety checklist, gain/frequency settings, metadata, fallback synthetic mode. |
| IQ recording | Manifest file, checksum, format description, reader script and analysis result. |

## Naming convention

Use stable names so that docs, scripts and figures remain predictable.

```text
docs/en/labs/lab-X-Y-short-name.md
docs/ru/labs/lab-X-Y-short-name.md
blocks/block_XX_topic/labs/lab_X_Y_short_name/
tools/generate_lab_X_Y_figures.py
docs/assets/labXY_result_name.png
```

For new public figures, prefer `docs/assets/` and use lower-case file names with hyphens or underscores.

## Bilingual rule

For each learner-facing page, keep a Russian and English version. The pages do not need to be literal translations, but they must stay structurally equivalent:

- same lab number;
- same objective;
- same input parameters;
- same expected plots and metrics;
- same safety assumptions;
- same report checklist.

## Reproducibility rule

A lab is reproducible when another learner can run it from a clean checkout using documented commands.

At minimum, provide:

```bash
python tools/tasks.py install
python tools/tasks.py docs
python tools/tasks.py labs
```

If the lab requires a special command, document it explicitly:

```bash
python path/to/script.py
cmake --build build
ctest --test-dir build -R lab_name
iverilog -g2012 -o build/tb_name path/to/tb.v path/to/dut.v
```

## Figure style

Course figures should follow an IEEE-like style:

- clear axes labels with units;
- readable font sizes;
- no unnecessary decorative effects;
- legends outside the data area when possible;
- deterministic data generation for CI;
- both engineering meaning and visual clarity.

Every generated figure should be connected to a script or reproducibility note.

## RF lab requirements

Any lab that touches RF hardware must include:

- RF path diagram;
- attenuation assumption;
- TX/RX gain values;
- center frequency and bandwidth;
- sample rate;
- receiver protection note;
- overload symptoms;
- fallback synthetic-data mode;
- reference to [RF safety guide](rf-safety.md).

## IQ dataset requirements

Any lab that uses real IQ data must include:

- dataset manifest;
- file format;
- sample rate;
- center frequency;
- checksum;
- source and hardware setup;
- license or access note;
- reference to [IQ dataset manifest guide](iq-dataset-manifest.md).

Use the template:

```text
templates/iq_dataset_manifest.template.yml
```

## Review checklist before merging a lab

- [ ] The lab has a clear engineering goal.
- [ ] RU and EN pages are aligned.
- [ ] Commands are copy-pasteable.
- [ ] Figures are reproducible or clearly marked as illustrative.
- [ ] Expected results are included.
- [ ] RF safety notes are present when needed.
- [ ] IQ metadata is present when needed.
- [ ] The page is linked from `mkdocs.yml`.
- [ ] The lab does not require large binary files in normal Git history.

## Recommended lab report ending

Each lab should end with a concise engineering conclusion:

```text
Conclusion:
- What was implemented or measured?
- Which metric proves correctness?
- What error sources remain?
- What should be changed before hardware deployment?
```
