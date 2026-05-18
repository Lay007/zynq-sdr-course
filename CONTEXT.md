# Project Context: Zynq SDR Course

This file defines the shared engineering context for AI-assisted work in this repository.

## Repository purpose

`zynq-sdr-course` is a bilingual RU/EN engineering course on Software-Defined Radio. It connects theory, executable DSP models, fixed-point reasoning, HDL/FPGA implementation, SDR hardware, RF measurement, IQ recording, practical electronics and final engineering reporting.

The repository is not only a set of notes. It is a reproducible engineering route for learning and demonstrating SDR systems.

## Core engineering route

Use this route as the default mental model for new content, labs, figures and documentation:

```text
theory -> modeling -> fixed-point -> HDL/FPGA -> RF frontend -> TX/RX -> synchronization -> IQ recording -> electronics -> integrated project
```

Russian wording:

```text
теория -> моделирование -> fixed-point -> HDL/FPGA -> радиотракт -> TX/RX -> синхронизация -> запись IQ -> электроника -> интегрированный проект
```

## Hardware baseline

Current practical setup:

- HAMGEEK / Zynq-7020 class SDR board with AD9363/ADR9363 RF frontend;
- RTL-SDR receiver for external reception checks;
- HDSDR for IQ recording and waterfall/spectrum inspection;
- MATLAB, Simulink, Python, C++, GNU Radio for analysis and modeling;
- Icarus Verilog for lightweight HDL smoke tests where possible.

## Documentation style

Documentation must be:

- bilingual when practical: English and Russian;
- readable in GitHub and MkDocs Material;
- focused on engineering credibility, not decorative text;
- structured around reproducible commands and expected results;
- supported by figures, tables, measurements or runnable examples where possible.

## Figure style

Figures should follow a clean IEEE-style engineering look:

- clear axes and units;
- readable font size;
- compact legends that do not overlap data;
- light background;
- consistent naming and captions;
- generated or reproducible when practical.

Avoid tiny labels, excessive horizontal chains, dark unreadable themes and decorative diagrams without measurement meaning.

## Lab quality bar

A strong lab should include:

1. purpose and engineering motivation;
2. theory summary;
3. executable model or script;
4. generated plots or measurable outputs;
5. relation to SDR/RF/FPGA practice;
6. verification or smoke-test command;
7. expected result;
8. short RU/EN summary when appropriate.

## CI and reproducibility

Before declaring a change complete, prefer running or documenting the closest available checks:

```bash
python tools/tasks.py docs
python tools/tasks.py labs
python tools/tasks.py hdl
python tools/tasks.py smoke
```

For documentation-only changes, `python tools/tasks.py docs` is the minimum expected check when local dependencies are available.

## AI-assisted work rules

When using AI agents or coding assistants:

- prefer small commits;
- do not rewrite unrelated files;
- diagnose before patching;
- add checks when fixing a regression;
- preserve the bilingual and engineering nature of the course;
- keep generated artifacts reproducible;
- cite commands used for validation in the final report or PR description.
