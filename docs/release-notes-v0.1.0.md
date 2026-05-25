# Release notes — v0.1.0

`v0.1.0` is the first public course release of `zynq-sdr-course`. The release establishes the repository as a bilingual engineering course that connects DSP theory, modeling, fixed-point design, HDL simulation, SDR hardware experiments, IQ recording and measurement-style analysis.

## Release theme

```text
theory -> modeling -> fixed-point -> HDL / FPGA -> SDR board -> RF path -> IQ capture -> analysis -> engineering report
```

The course is intentionally not only a collection of notes. It is structured as a reproducible engineering route with documentation, executable labs, CI checks, generated figures and hardware-facing safety guidance.

## What is included

### Documentation and site

- MkDocs + Material site structure.
- Russian and English learning paths.
- Main README entry points for English and Russian readers.
- Visual course map, portfolio view and system-level route pages.
- Course readiness and reproducibility pages.

### DSP foundation

The first release includes a stronger DSP backbone:

- FFT windows and spectral analysis;
- FIR low-pass filtering;
- digital mixing;
- decimation;
- FFT complexity and selected-bin detection;
- convolution vs correlation;
- window trade-offs for weak-signal detection.

### Fixed-point and FPGA bridge

The course includes early bridges from floating-point DSP models to hardware implementation:

- fixed-point FIR workflow;
- fixed-point digital mixer;
- HDL / FPGA workflow pages;
- streaming interface and testbench labs;
- FIR RTL mapping;
- NCO mixer RTL;
- AXI-Stream wrapper;
- float vs fixed vs RTL comparison.

### SDR and RF path

The release introduces the hardware-facing SDR route:

- RF frontend and AD9363 workflow;
- frequency planning;
- gain staging and overload discussion;
- synthetic RF capture analysis;
- RF impairment calibration;
- TX/RX chain architecture;
- DUC/DDC frequency translation;
- TX/RX loopback metrics;
- packet receiver detection;
- CIC decimator as a DSP -> fixed-point -> FPGA bridge.

### IQ recording and analysis

The course includes reproducible IQ-data discipline:

- IQ metadata guide;
- IQ dataset manifest guide;
- real-data policy;
- CI16 and multi-format IQ reader labs;
- generated synthetic IQ workflows;
- dataset manifest template;
- checksum-based reproducibility expectations.

### Safety and measurement discipline

The release adds engineering guardrails:

- RF safety guide;
- hardware bring-up checklist;
- measurement error notes;
- measurement uncertainty guide;
- SDR measurement report template;
- final measurement report labs and project templates.

### Executable course path

The release includes reproducible smoke checks through `tools/tasks.py` and `tools/run_all_labs.py`:

```bash
python tools/tasks.py docs
python tools/tasks.py labs
python tools/tasks.py hdl
python tools/tasks.py smoke
```

Representative executable labs generate figures and JSON metrics under `docs/assets`.

## Acceptance criteria for this release

`v0.1.0` is considered ready when:

- MkDocs builds in strict mode through CI;
- README files describe the current end-to-end course route;
- key labs include expected outputs or acceptance criteria;
- HDL smoke path is documented;
- RF safety and dataset policy are linked from the course structure;
- release notes summarize the current learning path;
- no large raw IQ captures are committed directly into normal Git history.

## Known limitations

- Real board-level Zynq/AD9363 captures are represented by synthetic or manifest-driven workflows until hardware validation data is added.
- Some advanced labs are roadmap-style and will continue to mature after this first release.
- The course currently prioritizes deterministic scripts and CI-friendly artifacts over notebook-first interactivity.

## Next release direction

The next milestone should focus on:

- one validated hardware capture path with Zynq/AD9363 and RTL-SDR/HDSDR;
- real IQ dataset manifests with checksums;
- model-vs-RTL comparison for CIC or another multirate DSP block;
- more complete measurement reports with EVM, SNR, BER and uncertainty budgets;
- polished final project examples.
