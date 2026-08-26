# Educational CSS accelerator contract

Issue [#46](https://github.com/Lay007/zynq-sdr-course/issues/46) is implemented
incrementally. The current course increment is a readable SF7 baseline:

```text
Q1.15 IQ stream
  -> registered saturating dechirp
  -> 128-sample symbol buffer
  -> explicit read-address/read-data boundary
  -> one-complex-MAC-per-cycle 128-point DFT core
  -> bin-valid/index/complex-value/magnitude stream
  -> peak and second-peak detector
```

`css_dft128_core.v` owns only the transform. It starts after a complete symbol
has been buffered, drives the buffer read address, and emits bins 0 through 127.
Its `start`, `busy`, and one-cycle `done` signals form the control boundary;
`start_rejected` pulses if another start is requested while a transform is
active. Reset aborts an in-flight transform and returns the core to idle. The
core has no dependency on the detector's storage or peak-search state.

## Interface and arithmetic

- A sample transfers when `valid_in && ready`.
- Exactly 128 accepted samples form one symbol; there is no overlap between load
  and DFT processing in this baseline.
- IQ and reference coefficients are signed Q1.15.
- Dechirp truncates after the Q2.30 complex multiply, saturates to Q1.15 and
  increments `dechirp_overflow_count` for every saturated sample.
- DFT samples and twiddles are signed 16-bit Q1.15. Each of the four real
  multiplies is signed 32-bit Q2.30, and each complex add/sub is explicitly
  widened to 33 bits before an arithmetic right shift by 15.
- Shifted complex terms accumulate in signed 32-bit registers; streamed real
  and imaginary bin values retain that width.
- Each accumulator is squared into a signed 64-bit product. The two products
  are added at 64-bit width to form `magnitude_squared`.
- The core does not saturate internally. With Q1.15 inputs and 128 samples, the
  shifted-term sum stays inside the signed 32-bit accumulator and the magnitude
  stays below the positive signed 64-bit limit. Inputs outside this contract do
  not have an overflow guarantee.
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

The standalone DFT regression checks reset/abort/restart behavior, start
rejection, all 128 bin events and indices, one-cycle valid pulses, X/Z-free
outputs, and every complex bin and magnitude against the shared Python
fixed-point reference. Its deterministic dechirped symbol-37 tone peaks at bin
37. The integrated detector regression covers all 128 noiseless SF7 symbols plus
deterministic CFO and noise cases. CI regenerates the detector inputs and
twiddle tables from the checked-in Python reference before simulation.

## Current limitations and next boundary

This implementation is a sequential educational DFT, not a
throughput-optimized FFT. RTL simulation proves the checked fixed-point and
control behavior; it does not prove Zynq-7020 timing closure, resource use, or
operation on hardware. No latency/sample-rate claim beyond simulated clock
cycles should be converted into a hardware rate without Vivado evidence.

The next datapath step is to replace `css_dft128_core` with a reusable FFT while
preserving the symbol-buffer read contract, the bin stream, and the independent
peak detector. Issue #46 still requires measured latency/throughput,
LUT/FF/BRAM/DSP utilization, timing and maximum sample-rate reports, AXI-Stream
data, AXI-Lite control/status, and a PS-side bring-up helper.

## Companion-project boundary

The complete LoRa-compatible, oversampled two-FFT correlator and the packet,
timestamp, ToA/TDoA and Zynq integration paths belong to
[`zynq-lora-phy-positioning`](https://github.com/Lay007/zynq-lora-phy-positioning).
See [ADR 0002](../../docs/adr/0002-css-lora-project-boundary.md). The two paths
must not be compared without accounting for their different goals and input
scaling.
