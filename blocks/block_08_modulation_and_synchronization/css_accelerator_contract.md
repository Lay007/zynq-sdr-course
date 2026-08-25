# Educational CSS accelerator contract

Issue [#46](https://github.com/Lay007/zynq-sdr-course/issues/46) is implemented
incrementally. The current course increment is a readable SF7 baseline:

```text
Q1.15 IQ stream
  -> registered saturating dechirp
  -> 128-sample symbol buffer
  -> one-complex-MAC-per-cycle 128-point DFT
  -> peak and second-peak search
```

## Interface and arithmetic

- A sample transfers when `valid_in && ready`.
- Exactly 128 accepted samples form one symbol; there is no overlap between load
  and DFT processing in this baseline.
- IQ and reference coefficients are signed Q1.15.
- Dechirp truncates after the Q2.30 complex multiply, saturates to Q1.15 and
  increments `dechirp_overflow_count` for every saturated sample.
- DFT products truncate by 15 bits into a signed 32-bit accumulator.
- Equal magnitudes use first-occurrence tie breaking.
- `done` is a one-cycle result pulse; result registers remain stable afterward.

The sequential DFT needs `128 * (128 + 1) = 16,512` MAC/finish cycles per
symbol, plus input/drain/done overhead. This is suitable for teaching fixed-point
behavior and establishing a bit-exact baseline, not a substitute for a reusable
streaming SF5–SF12 FFT.

## Reproduction

```bash
python blocks/block_08_modulation_and_synchronization/python/generate_css_sf7_detector_vectors.py
python tools/run_block8_css_rtl.py
```

The regression covers all 128 noiseless SF7 symbols plus deterministic CFO and
noise cases. Generated inputs and twiddle tables are ignored because CI rebuilds
them from the checked-in Python reference.

## Companion-project boundary

The complete LoRa-compatible, oversampled two-FFT correlator and the packet,
timestamp, ToA/TDoA and Zynq integration paths belong to
[`zynq-lora-phy-positioning`](https://github.com/Lay007/zynq-lora-phy-positioning).
See [ADR 0002](../../docs/adr/0002-css-lora-project-boundary.md). The two paths
must not be compared without accounting for their different goals and input
scaling.
