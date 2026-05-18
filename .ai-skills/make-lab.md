# Skill: Make or Improve a Course Lab

Use this skill when creating or improving SDR, DSP, FPGA, RF or measurement labs.

## Goal

Create labs that are educational, executable and connected to the full SDR engineering route.

## Required structure

A strong lab should contain:

1. title and short motivation;
2. learning goals;
3. theory summary;
4. signal/system model;
5. executable Python and/or MATLAB section when applicable;
6. fixed-point or implementation notes when applicable;
7. HDL/FPGA/RF connection when applicable;
8. plots or measurable outputs;
9. commands to run;
10. expected results;
11. common mistakes;
12. control questions;
13. short RU/EN summary when practical.

## Engineering route check

Before finishing, explicitly decide which route segments the lab covers:

```text
theory -> modeling -> fixed-point -> HDL/FPGA -> RF frontend -> TX/RX -> synchronization -> IQ recording -> electronics -> integrated project
```

The lab does not need to cover every segment, but it should explain how its topic connects to the larger route.

## Plot requirements

- Use readable IEEE-style figures.
- Label axes and units.
- Avoid legends that overlap data.
- Prefer generated plots over pasted screenshots.
- Store generated assets in the existing project convention.

## Validation

Prefer at least one of:

```bash
python tools/tasks.py labs
python tools/tasks.py docs
python tools/tasks.py smoke
```

If the lab includes Verilog, also consider:

```bash
python tools/tasks.py hdl
```

## Output format

Report:

- new or changed lab files;
- route segments covered;
- generated figures;
- commands used for validation;
- known limitations.

## Do not

- add theory-only pages when an executable demonstration is practical;
- add plots without explaining what they prove;
- create tiny unreadable diagrams;
- break bilingual navigation;
- hide assumptions about sample rate, carrier frequency, word length or signal format.
