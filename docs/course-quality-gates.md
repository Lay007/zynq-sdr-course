# Course quality gates

Use this checklist before merging course, lab, HDL, documentation, or tooling changes.

## Documentation quality

- Run the documentation build in strict mode before publishing.
- Keep navigation entries synchronized with created, renamed, or removed pages.
- Keep Russian and English sections structurally aligned when content exists in both languages.
- Prefer generated diagrams or source-controlled diagram descriptions over manually edited screenshots.
- Add captions and context for every figure that teaches a signal-processing or hardware concept.

## DSP and fixed-point quality

- State the reference floating-point behavior before adding fixed-point or HDL variants.
- Document word length, fractional length, rounding, saturation, and overflow assumptions.
- Include at least one deterministic test vector for non-trivial DSP blocks.
- Explain expected numerical error or tolerance when comparing models.
- Mention latency and throughput when a block is intended for FPGA implementation.

## HDL and FPGA quality

- Keep HDL examples small enough to understand in isolation.
- Add simulation notes or testbench guidance for hardware-facing blocks.
- Document clock, reset, valid/ready, and sample-rate assumptions.
- Avoid hiding vendor-specific behavior when a lab depends on a specific board or toolchain.

## SDR and RF lab quality

- Include RF safety and local regulation notes for transmitting examples.
- Prefer receive-only or low-power lab variants where possible.
- Record center frequency, sample rate, gain, bandwidth, and file format for IQ captures.
- Add dataset manifests or checksums when a lab uses recorded data.

## Review checklist

- Documentation build passes.
- Lab commands were checked for copy-paste usability.
- Figures are readable on GitHub and the MkDocs site.
- New files are linked from navigation or intentionally left unlisted.
- No private credentials, captures, hostnames, or personal paths are committed.
