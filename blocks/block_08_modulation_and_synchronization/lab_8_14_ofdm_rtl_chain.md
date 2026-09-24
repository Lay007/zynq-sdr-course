# Lab 8.14 - OFDM RTL: mapper to equalized loopback

## Goal

Take the [Lab 8.5](/zynq-sdr-course/en/labs/lab-8-5-ofdm-mini-link/) OFDM mini-link from a floating-point Python model to a synthesizable, self-checked fixed-point datapath: QPSK mapper, subcarrier allocator/extractor, a streaming radix-2 64-point IFFT/FFT, cyclic-prefix insertion/removal and a one-tap equalizer, each with its own Icarus Verilog testbench, composed into a full TX-to-RX digital loopback and a channel-equalized loopback.

This lab is the software/RTL half of issue #48. Read the [evidence boundary](#what-this-lab-does-and-does-not-prove) before treating any result here as a hardware measurement — it is not one.

## Why a second, RTL-level model of the same chain

[Lab 8.5](/zynq-sdr-course/en/labs/lab-8-5-ofdm-mini-link/) already proves the OFDM algorithm works in floating point. That is not the same claim as "this runs on the FPGA fabric." Every stage here exists twice, on purpose:

- once as a bit-exact Q1.15 fixed-point Python model (`tools/ofdm_ifft_fixed.py`, `tools/ofdm_fft_fixed.py`, `tools/ofdm_equalizer_fixed.py`) that tracks every rounding and saturation decision explicitly;
- once as synthesizable Verilog that is checked against the *same* committed vectors as that fixed-point model, not just against its own testbench's expectations.

That second copy is what makes "the RTL is correct" a falsifiable claim instead of an assumption. The `verification/vectors/block08_ofdm_*.mem` files are the shared ground truth: `tests/test_ofdm_ifft_fixed.py`, `tests/test_ofdm_fft_fixed.py` and `tests/test_ofdm_tx_fixed.py` check the Python model against them, and `tb_ofdm_ifft64_sequential.sv`/`tb_ofdm_fft64_sequential.sv` check the RTL against the same files — so a mismatch between Python and RTL cannot hide.

## TX chain

```mermaid
flowchart LR
    BITS["48 QPSK bit pairs"] --> MAP[ofdm_qpsk_mapper]
    MAP --> ALLOC[ofdm_subcarrier_allocator]
    ALLOC --> IFFT[ofdm_ifft64_sequential]
    IFFT --> CP[ofdm_cp16_inserter]
    CP --> OUT["80 Q1.15 samples/symbol"]
```

| Block | Role | Fixed-point / timing contract |
|---|---|---|
| `ofdm_qpsk_mapper.v` | 2 bits -> one Q1.15 QPSK symbol, matching Lab 8.5's `qpsk_from_bits` sign convention | magnitude `round(32767/sqrt(2)) = 23170`; 1-cycle latency |
| `ofdm_subcarrier_allocator.v` | Places 48 data symbols into a natural-order 64-bin IFFT frame and inserts the four pilot values (`pilot_ref = [+1,+1,+1,-1]`) at `k = -21,-7,+7,+21`, exactly like Lab 8.5's frequency-domain layout | collects 48 symbols, then emits bins 0..63; no new frame accepted mid-emission |
| `ofdm_ifft64_sequential.v` | Streaming radix-2 DIT IFFT, one `ofdm_ifft_butterfly` instance reused for all 6 stages x 32 butterflies | each butterfly divides by 2 -> normalized `1/64` scale; `total_saturation_count` accumulates clipped final components across all 192 butterflies |
| `ofdm_cp16_inserter.v` | Prepends samples `[48..63]` as the cyclic prefix | emits 80 samples/symbol (`out_is_cp` high for indices 0..15); `frame_error` if the input symbol was short |

`ofdm_tx_mapper_ifft_path.v` composes mapper -> allocator -> IFFT; `ofdm_tx_cp16_path.v` adds the CP stage and is the complete TX baseline used by the loopback tests below.

## RX chain

```mermaid
flowchart LR
    IN["80 Q1.15 samples/symbol"] --> CPR[ofdm_cp16_remover]
    CPR --> FFT[ofdm_fft64_sequential]
    FFT --> EXT[ofdm_subcarrier_extractor]
    EXT -->|data| EQ[ofdm_one_tap_equalizer]
    EXT -.->|pilot| PILOT["pilot phase tracker (coefficient not yet wired to EQ)"]
    EQ --> DEMAP[ofdm_qpsk_demapper]
    DEMAP --> BITS["recovered bit pairs"]
```

| Block | Role | Fixed-point / timing contract |
|---|---|---|
| `ofdm_cp16_remover.v` | Drops the 16-sample prefix, forwards samples 16..79 unchanged | fully backpressured on the 64 useful samples |
| `ofdm_fft64_sequential.v` | Scaled forward FFT, built by reusing the IFFT core via `FFT(x)/N = conj(IFFT(conj(x)))` | rare Q1.15 endpoint clips from conjugating `-32768` are counted, not hidden |
| `ofdm_subcarrier_extractor.v` | Splits the 64 bins into 48 data, 4 pilot and 12 null/guard carriers -- the exact inverse of the allocator's layout | data and pilot are independently backpressured sinks; a stalled pilot sink cannot stall data (or vice versa) |
| `ofdm_pilot_phase_tracker.v` | Turns each symbol's four pilots into a Q2.14 phase-correction coefficient (vectoring + rotation CORDIC) | sign-only pilot references, 14 CORDIC iterations, `pilot_ready` low for 31 cycles per symbol; bit-exact with `tools/ofdm_pilot_phase_tracker_fixed.py`; not yet wired to the equalizer |
| `ofdm_one_tap_equalizer.v` | Multiplies each data symbol by an externally supplied Q2.14 correction coefficient | Q1.15 x Q2.14 -> Q3.29, rounded to Q15 (nearest, half-LSB away from zero), then saturated; `saturation_count` is cumulative from reset |
| `ofdm_qpsk_demapper.v` | Hard-decision inverse of the mapper | transparent ready/valid, zero maps to bit `0` exactly like the Python reference |

## Fixed-point contract, in one place

Every sample in this chain is signed Q1.15 (`±1` represented as `±32767`/`-32768`, the usual asymmetric two's-complement endpoint). The one deliberate exception is the equalizer's correction coefficient, Q2.14, so a correction gain up to almost 2.0 can be represented without silently rescaling the signal path. Every arithmetic stage that can lose precision or range -- IFFT/FFT butterflies, the equalizer's complex multiply -- rounds explicitly (nearest, half-LSB away from zero) and saturates explicitly, and every saturation is *counted*, not just clamped: `total_saturation_count` on the TX/IFFT side, `total_saturation_count` + `conjugation_saturation_count` on the FFT side, `saturation_count` on the equalizer. That satisfies issue #48's "explicit scaling, saturation and overflow counters" requirement directly, and it is what makes the acceptance criterion below checkable rather than assumed:

> "No undocumented saturation at the selected back-off."

Every loopback test below asserts every one of these counters is exactly zero, and would fail loudly if any stage clipped silently.

## Streaming contract

Every block uses one clock, synchronous active-low reset, and a single-register ready/valid handshake: a producer must hold `valid` and its data stable until `ready` is also high, and a consumer's `ready` can depend combinationally on its own occupancy but not create a combinational loop back through `valid`. This is deliberately the same discipline the QPSK modem chain elsewhere in this course already uses. It is **not**, yet, packaged as AXI4-Stream: signal names are `valid`/`ready`/`re`/`im`/`index`/`last` rather than `tvalid`/`tready`/`tdata`/`tlast`, and there is no AXI4-Lite control/status register block exposing the saturation counters or a soft reset to a PS. `ofdm_tx_mapper_ifft_path.v`'s own header comment says as much: CP and "AXI-Stream" are named together as the next step, and CP has been added since; AXI packaging has not. Treat this as an open, scoped, and honestly reported item rather than a silent gap.

## Pilots: what exists and what does not yet

The allocator/extractor pair does real pilot **insertion and extraction**: the allocator writes the four fixed pilot values into their bins on TX, and the extractor produces a *separate* pilot stream on RX (`pilot_re`/`pilot_im`/`pilot_slot`/`pilot_ref_re`) alongside the data stream, exactly mirroring Lab 8.5's `pilot_k`/`pilot_ref`.

`ofdm_pilot_phase_tracker.v` consumes that pilot stream. Per OFDM symbol it forms `P = sum(sign(pilot_ref) * pilot)` (the references are +-1, so no multipliers), finds `angle(P)` with a 14-iteration vectoring CORDIC, and turns it into the correction coefficient `16384 * exp(-j * angle(P))` in Q2.14 with a rotation CORDIC, which is the input format of `ofdm_one_tap_equalizer`. It is the fixed-point form of Lab 8.5's `pilot_phase = angle(vdot(pilot_ref, y_eq[pilots]))`. `pilot_ready` drops for the 31 cycles of computation, and an all-zero pilot sum returns the identity coefficient with a `zero_energy` flag.

It is verified like the rest of the chain: `tools/ofdm_pilot_phase_tracker_fixed.py` is the bit-exact model, `tools/generate_ofdm_pilot_tracker_vectors.py` writes 49 test symbols (every 15 degrees, the +-90 and +-180 degree edges, amplitudes 300 to 32000, zero energy, and noisy symbols whose four pilots disagree), and `tb_ofdm_pilot_phase_tracker.sv` requires a bit-exact match while holding `pilot_valid` high through the busy cycles:

```bash
python -m pytest tests/test_ofdm_pilot_phase_tracker_fixed.py
python -m tools.generate_ofdm_pilot_tracker_vectors   # regenerate the committed vectors
python tools/run_ofdm_rtl.py                          # all OFDM benches, including the tracker
```

```text
PASS: ofdm_pilot_phase_tracker matched the fixed-point model on 49 symbols (backpressure cycles 1490)
```

Against the ideal `exp(-j * theta)`, the coefficient is within 7 LSB of 16384 (0.04 %) and the phase within 3 units of pi/2^15 (about 3e-4 rad) at every whole degree.

What is still **not** in RTL: the coefficient belongs to the symbol whose pilots produced it, but that symbol's data has already streamed past by the time the last pilot (bin 57) arrives. Applying it to the same symbol needs a one-symbol data buffer; applying it to the next symbol gives tracking with a one-symbol lag. Neither wiring exists yet, the loopback tests below still give the equalizer a fixed coefficient, and there is no per-subcarrier channel estimate for a frequency-selective channel.

## Verification stage 1: float model vs. fixed-point model vs. RTL

```bash
python -m pytest tests/test_ofdm_ifft_fixed.py tests/test_ofdm_fft_fixed.py \
  tests/test_ofdm_equalizer_fixed.py tests/test_ofdm_tx_fixed.py -q
```

These tests check the Q1.15 Python model's arithmetic (including saturation counts) against the committed `verification/vectors/block08_ofdm_*.mem` files. The RTL testbenches below check the *same* files, so a pass on both sides is a bit-exact three-way match: float intent -> fixed-point reference -> synthesizable RTL.

## Verification stage 2: self-checking RTL digital loopback

Every block has its own testbench; run the two end-to-end ones directly with Icarus Verilog:

```bash
RTL=blocks/block_08_modulation_and_synchronization/rtl
TB=blocks/block_08_modulation_and_synchronization/tb

iverilog -g2012 -o /tmp/tb_ofdm_loop.vvp \
  $RTL/ofdm_qpsk_mapper.v $RTL/ofdm_subcarrier_allocator.v \
  $RTL/ofdm_ifft_butterfly.v $RTL/ofdm_ifft64_sequential.v \
  $RTL/ofdm_tx_mapper_ifft_path.v $RTL/ofdm_cp16_inserter.v \
  $RTL/ofdm_tx_cp16_path.v $RTL/ofdm_cp16_remover.v \
  $RTL/ofdm_fft64_sequential.v $RTL/ofdm_subcarrier_extractor.v \
  $RTL/ofdm_qpsk_demapper.v \
  $TB/tb_ofdm_tx_rx_digital_loopback.sv
vvp /tmp/tb_ofdm_loop.vvp
```

The loopback through a +90-degree channel and the one-tap equalizer is a separate testbench:

```bash
iverilog -g2012 -o /tmp/tb_ofdm_eq_loop.vvp \
  $RTL/ofdm_qpsk_mapper.v $RTL/ofdm_subcarrier_allocator.v \
  $RTL/ofdm_ifft_butterfly.v $RTL/ofdm_ifft64_sequential.v \
  $RTL/ofdm_tx_mapper_ifft_path.v $RTL/ofdm_cp16_inserter.v \
  $RTL/ofdm_tx_cp16_path.v $RTL/ofdm_cp16_remover.v \
  $RTL/ofdm_fft64_sequential.v $RTL/ofdm_subcarrier_extractor.v \
  $RTL/ofdm_one_tap_equalizer.v $RTL/ofdm_qpsk_demapper.v \
  $TB/tb_ofdm_tx_rx_equalized_loopback.sv
vvp /tmp/tb_ofdm_eq_loop.vvp
```

Or run the whole Block 8 OFDM suite the same way CI does:

```bash
bash -c '
RTL=blocks/block_08_modulation_and_synchronization/rtl
TB=blocks/block_08_modulation_and_synchronization/tb
for pair in \
  "tb_ofdm_qpsk_mapper:$RTL/ofdm_qpsk_mapper.v" \
  "tb_ofdm_subcarrier_allocator:$RTL/ofdm_subcarrier_allocator.v" \
  "tb_ofdm_ifft_butterfly:$RTL/ofdm_ifft_butterfly.v" \
  "tb_ofdm_cp16_inserter:$RTL/ofdm_cp16_inserter.v" \
  "tb_ofdm_cp16_remover:$RTL/ofdm_cp16_remover.v" \
  "tb_ofdm_subcarrier_extractor:$RTL/ofdm_subcarrier_extractor.v" \
  "tb_ofdm_one_tap_equalizer:$RTL/ofdm_one_tap_equalizer.v" \
  "tb_ofdm_qpsk_demapper:$RTL/ofdm_qpsk_demapper.v"; do
  name="${pair%%:*}"; src="${pair#*:}"
  iverilog -g2012 -o "/tmp/$name.vvp" $src "$TB/$name.sv" && vvp "/tmp/$name.vvp"
done'
```

Measured results (reproduced by the commands above, on this repository's current RTL):

```text
PASS: OFDM TX->RX digital loopback recovered 96/96 bits with zero errors
PASS: OFDM +90deg channel -> -90deg equalizer recovered 96/96 bits, BER=0
```

The second result is not a trivial passthrough: the testbench applies a genuine +90-degree complex rotation to every transmitted sample in the time domain (`channel_re = -im, channel_im = re`), and the equalizer is given the exact inverse coefficient (`W = -j` in Q2.14) to undo it. Every saturation counter (`tx_saturation_count`, `fft_saturation_count`, `eq_saturation_count`) is asserted to be exactly zero in the same test, so "BER=0" is not concealing an overflow that happened to cancel out numerically.

## What this lab does and does not prove

This closes, in simulation only, issue #48's Initial RTL scope (mapper, subcarrier allocator/extractor, streaming 64-point IFFT/FFT, CP insertion/removal, one-tap equalizer, explicit scaling/saturation/overflow counters) and Verification stages 1-2 (float vs. fixed-point, self-checking digital loopback) with real, reproducible, measured evidence: 96/96 bits at BER=0 for both the plain digital loopback and a loopback through a genuine complex channel rotation with the equalizer actually correcting it.

It does **not** claim:

- AXI4-Stream/AXI4-Lite packaging (signal-compatible ready/valid exists; the AXI naming, an AXI4-Lite control/status block and Vivado integration do not);
- automatic pilot-driven correction in the RTL datapath: `ofdm_pilot_phase_tracker.v` computes the per-symbol phase coefficient (bit-exact with its model), but it is not yet wired into the equalizer, and there is no per-subcarrier channel estimate;
- Verification stages 3-5 (PL/fabric loopback on Zynq, safe attenuated AD9361/AD9363 cabled loopback, an independent SDR capture) -- these need the physical board and RF path, neither of which was available while writing this lab;
- that the transforms run at 100 MHz. A Vivado 2021.1 out-of-context implementation on `xc7z020clg400-2` ([report](https://github.com/Lay007/zynq-sdr-course/blob/main/reports/fpga/block8-ofdm-vivado-evidence.md)) routes every OFDM block without DRC errors, and the equalizer, pilot tracker and CP remover meet 100 MHz comfortably. But `ofdm_tx_cp16_path` and `ofdm_fft64_sequential` miss it by about 10 ns (post-route WNS -10.2 / -10.8 ns, roughly 49 / 48 MHz, about 8.8k LUT each): the shared butterfly multiplies, rounds, saturates and updates its saturation counter in one clock (28 logic levels), and the 64-point working memory sits in fabric logic, not block RAM. Pipelining the butterfly changes the IFFT schedule and is not done yet. The per-block header comments state cycle-level latency (for example the IFFT's `384 compute clocks after input collection`).

## Exercises

Each exercise changes the equalizer coefficient on line `.coeff_re(16'sd0), .coeff_im(-16'sd16384)` of `tb_ofdm_tx_rx_equalized_loopback.sv` (Q2.14, so 16384 = 1.0). The outputs below were observed with Icarus Verilog 12.0.

1. Use the wrong sign, `W = +j` (`.coeff_im(16'sd16384)`). The channel and the equalizer now add up to 180 degrees: `FAIL BER nonzero: 96/96 bit errors`. Every bit is inverted.
2. Turn the equalizer off, `W = 1` (`.coeff_re(16'sd16384), .coeff_im(16'sd0)`), or use `W = -1`. The residual rotation is +90 or -90 degrees: `48/96 bit errors` in both cases. With Gray QPSK a quarter turn flips exactly one of the two bits of every symbol.
3. Correct only half of the rotation, `W = exp(-j pi/4)` (`.coeff_re(16'sd11585), .coeff_im(-16'sd11585)`). The residual is 45 degrees and the points land on the axes (the first failing value is `EQ=(513,1)`): `22/96 bit errors`. Explain why this is the worst case for a hard decision and why the count is not exactly 48.
4. In a real receiver the coefficient is not given by the testbench. Which OFDM symbols or subcarriers would you use to estimate it, and how does Lab 8.5 do it in Python?

## Report checklist

- [x] Float vs. fixed-point bit-exact match (shared committed vectors).
- [x] Self-checking RTL digital loopback, BER=0, reproducible.
- [x] Self-checking RTL equalized loopback through a real complex channel, BER=0, reproducible.
- [x] Every saturation/overflow counter asserted zero at the tested back-off.
- [ ] AXI4-Stream/AXI4-Lite packaging.
- [x] Pilot phase tracker in RTL, bit-exact with its fixed-point model (49 symbols).
- [ ] Tracker coefficient wired into the equalizer; per-subcarrier channel estimation.
- [ ] PL/fabric loopback on Zynq.
- [ ] Safe attenuated AD9361/AD9363 cabled loopback with attenuation/gain metadata.
- [x] Resource and timing report from Vivado OOC implementation (all blocks routed; the IFFT/FFT paths miss 100 MHz).
- [ ] Pipelined butterfly and block-RAM working memory that meet 100 MHz.
