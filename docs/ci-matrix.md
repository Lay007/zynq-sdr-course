# CI Matrix

This page documents what each GitHub Actions workflow validates and which artifacts it produces.

## Workflow overview

| Workflow | Trigger focus | Main checks | Main artifacts |
|---|---|---|---|
| `full_course_smoke.yml` | broad course changes | MkDocs strict build, representative Python labs, Block 5 HDL smoke | reproducibility summary, selected plots |
| `python_quality.yml` | Python changes | formatting/linting and Python quality gates | PASS/FAIL logs |
| `block4_labs.yml` | fixed-point lab block | Lab 4.1 and 4.2 executable Python models | fixed-point FIR/mixer figures |
| `block5_hdl.yml` | HDL/FPGA block | Icarus Verilog compilation and self-checking testbenches | VCD files, PASS/FAIL logs |
| `hdl-canonical-ci.yml` | canonical HDL vectors | generated vectors and HDL smoke path | canonical vector logs |
| `block6_rf_analysis.yml` | RF frontend lab block | Lab 6.4 synthetic RF analysis | spectrum/time plots, metrics JSON |
| `block7_tx_rx.yml` | TX/RX chain block | Lab 7.2 and 7.3 executable models | frequency-plan/spectrum plots, loopback metrics |
| `block8_sync.yml` | synchronization labs | CFO, phase, timing and end-to-end sync models | constellation plots, EVM/BER metrics |
| `block9_recording_analysis.yml` | IQ recording labs | CI16 reader and multi-format IQ reader | spectrum plots, metrics JSON, synthetic captures |
| `qpsk_demo_analysis.yml` | generated QPSK replay dataset | deterministic dataset generation, analyzer run and metric thresholds | constellation SVG, spectrum SVG, analysis summary JSON |
| `dataset_manifests.yml` | dataset metadata | dataset manifest parsing, Git LFS pointer and checksum rules | manifest validation report |
| `docs-assets-check.yml` | markdown asset integrity | local markdown asset links | PASS/FAIL report |
| `experiment-manifests-check.yml` | manifest consistency | YAML structure and required fields in `experiments/*.yaml` | PASS/FAIL report |
| `pages.yml` / docs deploy | documentation | MkDocs site build and GitHub Pages deploy | published course site |
| `generate_ieee_plots.yml` | demo figures | generated IEEE-style plots | `docs/assets/*.png` |

## Full Course Smoke

Purpose: verify that the repository still works as an integrated engineering course.

Checks:

- `mkdocs build --strict`;
- representative executable Python labs through `tools/run_all_labs.py`;
- Block 5 HDL smoke tests with Icarus Verilog;
- reproducibility summary artifacts.

Local equivalent:

```bash
python tools/tasks.py smoke
```

## Python Quality

Purpose: catch basic Python regressions before the broader course smoke path.

Checks typically include:

- Ruff configuration from `pyproject.toml`;
- pytest coverage for repository-level utilities and regression checks;
- import/runtime sanity for course helpers when they are included in the test set.

Local equivalent:

```bash
python tools/run_local_ci.py --quick
```

## Block 4 Labs

Purpose: verify fixed-point executable labs and generated figures.

Checks:

- Lab 4.1 fixed-point FIR model;
- Lab 4.2 fixed-point digital mixer model;
- generated-figure existence checks.

## Block 6 RF Analysis

Purpose: verify synthetic RF capture analysis and its metrics artifacts.

Checks:

- Lab 6.4 executable model;
- generated PNG and JSON artifacts.

## Block 7 TX/RX

Purpose: verify TX/RX chain modeling and loopback metrics generation.

Checks:

- Lab 7.2 DUC/DDC model;
- Lab 7.3 loopback metrics model;
- generated PNG and JSON artifacts.

## Block 5 HDL

Purpose: verify synthesizable/educational Verilog examples and self-checking testbenches.

The HDL smoke flow is documented in [HDL Smoke Verification](./verification/hdl_smoke.md).

Checks:

- `iq_passthrough`;
- `fir_iq_4tap`;
- `nco_mixer_iq`;
- `axis_iq_passthrough`;
- BPSK chain and control-wrapper smoke tests when canonical vectors are regenerated.

Local equivalent:

```bash
make hdl
```

## QPSK Demo Analysis

Purpose: keep the synthetic QPSK replay dataset reproducible and useful for Block 9/11/12 reports.

Checks:

- generate the deterministic CI16 fixture;
- run the analyzer;
- verify the summary JSON and preview SVG files exist;
- enforce basic metric thresholds for sample count, symbol count, EVM and CFO.

Local equivalent:

```bash
python tools/generate_demo_qpsk_dataset.py
python tools/analyze_demo_qpsk_dataset.py
```

## Dataset Manifests

Purpose: keep dataset descriptors consistent without committing unnecessary binary payloads.

Checks:

- parse dataset manifests;
- verify required metadata fields;
- check Git LFS pointer rules and checksum fields when present.

Local equivalent:

```bash
python tools/check_dataset_manifests.py
```

## Block 8 Synchronization

Purpose: verify synchronization models and generated metrics.

Checks:

- Lab 8.1 CFO correction;
- Lab 8.2 phase correction;
- Lab 8.3 timing recovery;
- Lab 8.4 end-to-end sync chain.

Artifacts:

- constellation plots;
- phase/timing plots;
- EVM/BER metrics JSON.

## Block 9 Recording Analysis

Purpose: verify metadata-driven IQ capture processing.

Checks:

- Lab 9.2 CI16 reader;
- Lab 9.3 multi-format IQ reader.

Artifacts:

- FFT spectrum plots;
- CI16/CU8/CF32 synthetic capture metrics;
- quality checks for SNR, DC and clipping.

## Documentation build

Purpose: keep the bilingual MkDocs site consistent.

Checks:

- navigation references;
- snippet includes;
- Mermaid-friendly markdown structure;
- strict-mode warnings.

Local equivalent:

```bash
python tools/tasks.py docs
```

## Docs Assets Check

Purpose: fail fast on broken local markdown asset links.

Checks:

- run `tools/check_markdown_assets.py`;
- verify referenced local assets exist.

## Experiment Manifests Check

Purpose: keep experiment manifests machine-checkable and reproducible.

Checks:

- parse every `experiments/*.yaml`;
- validate required fields and template paths;
- enforce unique and filename-aligned `experiment.id`.

## When to add a new workflow

Add a dedicated workflow when a new block has:

- executable models with generated artifacts;
- HDL testbenches;
- external tool assumptions;
- long-running checks that should not always run in `full_course_smoke.yml`.

## CI quality checklist

- [ ] Workflow has a clear name.
- [ ] Trigger paths are scoped.
- [ ] Dependencies are explicit.
- [ ] Generated artifacts are validated.
- [ ] Artifacts are uploaded when useful.
- [ ] Local equivalent command is documented.
