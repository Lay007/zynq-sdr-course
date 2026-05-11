# Contributing

Thank you for improving the Zynq SDR Course. This repository is structured as an engineering course, so every contribution should improve clarity, reproducibility or measurement value.

## Before contributing

Run the local smoke path when possible:

```bash
python -m pip install -r requirements.txt
make docs
make labs
```

For HDL-related changes, also run:

```bash
make hdl
```

For the full local check:

```bash
make smoke
```

## Course structure

Course content is organized by blocks:

```text
blocks/block_XX_topic/
docs/ru/...
docs/en/...
```

A new lab should usually include:

- source material under `blocks/block_XX_topic/`;
- a Russian MkDocs wrapper under `docs/ru/labs/`;
- an English MkDocs wrapper under `docs/en/labs/`;
- navigation update in `mkdocs.yml`;
- executable script or clear manual procedure when applicable;
- generated artifacts or expected report artifacts;
- a report checklist.

## Python lab guidelines

Python labs should:

- run from the repository root;
- use deterministic random seeds;
- write figures and metrics to `docs/assets`;
- write machine-readable metrics as JSON;
- avoid large binary outputs in Git;
- be callable from CI when practical.

## Verilog / HDL guidelines

HDL labs should:

- include a self-checking testbench;
- generate or commit small deterministic vectors;
- document latency, reset behavior and fixed-point formats;
- run under Icarus Verilog when possible;
- avoid vendor-only dependencies in baseline labs.

## Documentation guidelines

Documentation should:

- prefer diagrams-as-code when possible;
- include clear engineering assumptions;
- state units for all metrics;
- include report checklists;
- avoid unsupported claims;
- keep Russian and English navigation consistent.

## Real data policy

Do not commit large raw IQ captures. Use metadata, external links and checksums. See:

```text
docs/real-data-policy.md
templates/capture_metadata.template.json
```

## Commit style

Prefer focused commits:

```text
Add Lab 8.5 sample-rate offset model
Fix Block 5 AXI testbench handshake check
Add dataset registry entry for AD9363 QPSK loopback
```

## Pull request checklist

- [ ] MkDocs builds in strict mode.
- [ ] New pages are linked in `mkdocs.yml`.
- [ ] Scripts run from repository root.
- [ ] Generated artifacts are documented.
- [ ] Metadata is included for IQ/data workflows.
- [ ] Russian and English navigation remain consistent.
