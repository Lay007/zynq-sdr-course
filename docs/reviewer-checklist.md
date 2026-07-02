# Reviewer Acceptance Checklist

This checklist is intended for a fast but meaningful technical review of the course. It helps a reviewer decide whether a lab, block, or final project is only a demonstration or already has engineering evidence.

## 1. Reproducibility

A reviewed result should answer these questions:

- Can the result be rebuilt from a clean clone?
- Is the command documented near the artifact that it generates?
- Are generated plots, CSV files, and reports separated from source inputs?
- Are large IQ captures referenced through manifests instead of being committed to Git?

Minimum evidence:

```bash
python tools/tasks.py install
python tools/tasks.py docs
python tools/tasks.py smoke
```

## 2. DSP correctness

For DSP-oriented material, check that the lab states:

- sampling rate and units;
- signal model and assumptions;
- expected spectrum, bandwidth, or time-domain behavior;
- tolerance or acceptance rule for numerical comparison;
- known limitations of the simplified model.

A good lab should not only produce a figure. It should explain what engineering decision follows from the figure.

## 3. Fixed-point readiness

Before moving from floating-point modeling to FPGA-oriented work, check that the material records:

- selected Q-format or word length;
- scaling strategy;
- rounding and saturation behavior;
- overflow risk;
- comparison against a floating-point reference;
- acceptable error budget.

## 4. HDL / FPGA evidence

For HDL-facing blocks, the minimum useful evidence is:

- source module path;
- testbench path;
- input vector source;
- expected output vector or assertion rule;
- latency note;
- CI or local command that runs the smoke test.

For hardware-ready work, add resource and timing notes:

- target FPGA or Zynq family;
- clock target;
- LUT / FF / DSP / BRAM estimate;
- timing status;
- known synthesis limitations.

## 5. RF and measurement discipline

For RF experiments, check that the report includes:

- board and RF frontend version;
- carrier frequency, sample rate, bandwidth, gain settings;
- attenuation and safety notes;
- capture format and metadata;
- independent observation receiver when possible;
- explicit quality metrics and a conclusion tied to those metrics.

## 6. Digital-link metric gate

For digital communication labs, SNR alone is not sufficient. A reviewed BPSK/QPSK/OFDM result should include:

| Evidence | Required? | Why |
|---|---:|---|
| SNR or noise estimate | yes | Shows signal margin, but not bit correctness. |
| EVM or constellation metric | yes | Shows modulation quality and residual distortion. |
| BER or FER | yes | Shows whether the receiver recovered bits or frames correctly. |
| Compared bits or frames | yes | Gives statistical weight to BER/FER. |
| Frame-sync status | yes | Prevents false conclusions from shifted payload comparison. |
| CFO/timing notes | when relevant | Explains failures that can occur even at high SNR. |

A result with only SNR may be accepted as a spectrum or signal-presence check, but not as a validated digital link.

## 7. Final-project acceptance gate

A portfolio-ready final project should include:

| Evidence | Required? | Notes |
|---|---:|---|
| Problem statement | yes | What is being demonstrated and why |
| Reproducible model | yes | MATLAB/Python/C++ reference or equivalent |
| Fixed-point or implementation note | yes | Required for FPGA-facing work |
| HDL or software implementation | yes | Depending on project scope |
| Verification results | yes | Tests, plots, CSVs, logs |
| Measurement report | recommended | Required for RF/hardware projects |
| Limitations | yes | What is not proven yet |
| Next steps | yes | Clear technical continuation path |

## 8. Review decision

Use the following decision levels:

- **Draft** - concept exists, but evidence is incomplete.
- **Runnable** - commands work from a clean clone.
- **Verified** - outputs are checked against deterministic references or tolerances.
- **Hardware-oriented** - implementation constraints and FPGA/RF assumptions are documented.
- **Portfolio-ready** - a reviewer can understand the problem, reproduce the result, and trust the conclusion.
