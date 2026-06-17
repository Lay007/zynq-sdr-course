# HDL Smoke Verification

This page documents the lightweight HDL smoke flow used for Block 5 FPGA examples.

The goal is to keep local verification and GitHub Actions aligned: the same shell runner is used by the `Makefile` and by CI workflows.

## Entry point

```bash
bash tools/run_block5_hdl_smoke.sh
```

The runner performs the following steps:

1. Generate deterministic FIR IQ 4-tap vectors.
2. Generate deterministic NCO mixer IQ vectors.
3. Check that the generated vector files are present and non-empty.
4. Compile and run `iq_passthrough` with Icarus Verilog.
5. Compile and run `fir_iq_4tap` with Icarus Verilog.
6. Compile and run `nco_mixer_iq` with Icarus Verilog.
7. Compile and run `axis_iq_passthrough` with Icarus Verilog.

## Local usage

Run only the HDL smoke suite:

```bash
make hdl
```

Run the broader local smoke target:

```bash
make smoke
```

Clean generated HDL artifacts:

```bash
make clean
```

## CI usage

The same runner is used by these workflows:

- `.github/workflows/block5_hdl.yml`
- `.github/workflows/hdl-canonical-ci.yml`
- `.github/workflows/full_course_smoke.yml`

Keeping one runner avoids drift between local commands and CI commands. When a new Block 5 HDL testbench is added, update `tools/run_block5_hdl_smoke.sh` first, then keep workflow files thin.

## Scope

This smoke suite is intentionally small. It checks that representative HDL modules compile, run, and consume deterministic vectors. It is not a replacement for full timing closure, board-level validation, or vendor-tool synthesis.

## Expected artifacts

Typical generated files include:

- `blocks/block_05_fpga_hdl_flow/tb/*_vectors.txt`
- `blocks/block_05_fpga_hdl_flow/tb/*.out`
- `blocks/block_05_fpga_hdl_flow/tb/*.vcd`
- waveform files emitted by the testbenches

These files are build artifacts and should not be edited manually.
