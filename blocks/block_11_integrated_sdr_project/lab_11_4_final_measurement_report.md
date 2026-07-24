# Lab 11.4 — Final Measurement Report

## Goal

The final engineering report for the integrated SDR project: an in-fabric QPSK modem on the
Zynq-7020 + AD9361, validated on a two-board over-cable RF link.

## Engineering question

> Does the project provide enough evidence that the SDR chain works as intended?

**Yes.** A synthesized PL modem recovers a known frame at BER 0 on every cold boot through the fabric
loopback, and on a two-board RF link it decodes a continuously transmitted frame with no catastrophic
(whole-burst) failures and a payload BER of ~4×10⁻⁴. The evidence is deterministic, statistical, and
reproducible from committed scripts.

## Abstract

A deterministic QPSK burst is generated in the PL (frame ROM → differential encoder → RRC → DAC),
transmitted by board A over a contained SMA cable + 30 dB attenuator at 915 MHz, and received by
board B, whose in-fabric RX chain (DC blocker → matched filter → feedforward phase pick → Gardner
timing recovery → coarse CFO → Costas carrier recovery → hard decision → differential decoder →
quadrant-resolving BER counter) recovers the frame and scores it on-chip. The link closes at BER 0 in
the coherent fabric loopback and at ~4×10⁻⁴ over the two independent-reference RF front ends, with the
whole-burst rotation failures eliminated by differential coding plus a lengthened preamble.

## Architecture

```text
Board A (TX)                          Board B (RX, in-fabric modem)
 frame ROM (512b)                      AD9361 RX1 ─ ADC
   │ diff-encode (host)                  │
   │ QPSK map + RRC (SPS=8)              DC blocker (running-avg LO-leakage removal)
   │ iio_writedev -c (cyclic)            │  matched RRC FIR
 AD9361 TX1 ─ DAC ── SMA + 30 dB ──►     │  feedforward phase picker
                     attenuator          │  Gardner symbol-timing recovery
                                         │  coarse CFO (4th-power feedforward)
                                         │  Costas carrier recovery (gp_ctrl[10])
                                         │  hard decision → differential decoder (gp_ctrl[17])
                                         │  quadrant-resolving BER counter + position telemetry
                                        gpreg @ 0x79040000 (host reads counts)
```

Runtime feature gates live in `gp_ctrl` (DC block, Costas, coarse CFO, phase pick, Gardner,
payload-position readout, decoded-bit readout, differential mode). The control/status plane is the
`axi_gpreg` window at `0x79040000`.

## Method

- **Simulation / RTL:** every block has an Icarus testbench; the full block-5 suite is 36/36, several
  benches driven by real on-board captures (`tb_qpsk_rx_costas`, `tb_qpsk_costas_stress`,
  `tb_qpsk_two_board_residual_cfo`). Offline bit-exact models (`dc_blocker_margin.py`,
  `lab_11_43_dqpsk_model.py`) back the RTL.
- **RF:** two boards, board A the vendor Pluto image (continuous `iio_writedev` TX), board B the course
  boot image (in-fabric RX). The frame is rebuilt bit-exact in Python from the same ROM the RTL reads.
- **Recording / scoring:** the on-chip BER counter scores each burst; the host reads counts over gpreg
  (`qpsk_ber_once`). Position telemetry (`gp_ctrl[15]`) and decoded-bit readout (`gp_ctrl[16]`) localise
  errors.

## Setup

| Parameter | Value |
|---|---|
| Carrier | 915 MHz |
| Sample rate | 3.84 MHz (SPS = 8) |
| Symbol rate | 480 kSym/s, QPSK (Gray) |
| TX gain | −30 dB into a 30 dB attenuator (contained SMA cable) |
| RX gain | 50 dB, manual |
| Frame | 152 symbols = 24-symbol preamble + 256-bit payload (long-preamble differential) |
| Idle safety | both boards restored to −89.75 dB after every test |
| Part / tools | xc7z020clg400-2, Vivado 2021.1, timing WNS +0.036 ns (shipped diff image) |

## Results

**Fabric loopback (coherent, deterministic), cold-boot campaign:** 50/50 cold boots decode cleanly;
BPSK+QPSK combined **5,610,000 bits, 0 errors → BER < 5.34×10⁻⁷** (95 % one-sided, rule of three).

**Two-board RF link (A TX1 → 30 dB → B RX1), 915 MHz:**

| Configuration | Clean frames | Gross (whole-burst rotation) | Payload BER |
|---|---:|---:|---:|
| absolute, lock-tol=1 (140/24) | 98.9 % (1182/1195) | 0.75 % | ~3×10⁻³ |
| **differential + 24-sym preamble (152/48)** | 96.9–98.8 % | **0 %** | **~4×10⁻⁴** |

**Carrier / frequency:** intrinsic inter-board CFO measured −194 / −238 / −288 Hz across three cold
boots; the coarse-CFO estimator tracks a deliberately injected offset over the full ±60 kHz
unambiguous range (Lab 11.31), and the Costas loop removes the residual so the constellation is
stationary through the frame.

### Minimum figures (artifacts)

- architecture diagram — above;
- TX/RX frequency plan — Setup table;
- FFT / constellation — `docs/assets/lab1132_two_board_fabric_coarse_cfo.png` and the capture-tap
  readers (`capture_tap_symbol_margin.py`);
- BER summary — `docs/assets/lab1142_ber_floor_live.json`, `lab1145_diff_long_preamble_live.json`;
- reproducibility — the `lab_11_30…11_45` scripts.

## Pass/fail table

| Criterion | Target | Measured | Status |
|---|---:|---:|---|
| frequency error (residual after recovery) | ≈ 0 (loop stationary) | intrinsic ~200–300 Hz, tracked; ±60 kHz range | PASS |
| SNR / decision margin | positive margin on every axis | normalised decision margin ~0.97 (median), no axis < 0 | PASS |
| EVM | (not separately instrumented) | end-to-end quality captured by BER | n/a |
| BER (two-board) | functional link, no catastrophic loss | 4.5×10⁻⁴, 0 gross | PASS |
| BER (fabric loopback) | ≈ 0 | < 5.34×10⁻⁷ over 5.6 M bits | PASS |
| clipping fraction | 0 | TX at 0.70×full-scale; RX not railed | PASS |

## Discussion — limitations and error sources

- **Differential penalty.** Differential QPSK costs the inherent ~3 dB (each symbol error → two bit
  errors), seen as a residual intermittent single-bit rate that keeps the clean-frame count at
  ~97–99 % rather than 100 %. It is not a rotation failure. The trade is worth it: the catastrophic
  ~46 %-BER bursts are gone and aggregate BER drops an order of magnitude.
- **Adaptive-loop transient.** Differential decoding reads the phase difference between consecutive
  symbols, so any RX loop still settling in the early payload corrupts it. The fix (a 24-symbol
  preamble so the payload starts past acquisition) is documented in Lab 11.45; a longer 32-symbol
  preamble is worse (lock rate falls past the sampler margin).
- **AD9361 cold-reset dependency.** A warm reboot leaves the BBPLL in calibration timeout; a physical
  power cycle is required after loading a new PL image.
- **SNR/EVM not separately instrumented.** BER is the reported end-to-end quality metric; a dedicated
  EVM capture is a possible future addition.

## Reproducibility

```text
# board A (vendor Pluto) streams the long-preamble differential frame; board B (course) scores it
cd blocks/block_11_integrated_sdr_project/python
python lab_11_45_differential_long_preamble.py            # -> docs/assets/lab1145_diff_long_preamble_live.json
python lab_11_42_ber_floor_lock_tolerance.py --predict     # false-lock arithmetic, no bench
python tools/run_block5_hdl_smoke.py                       # RTL suite, 36/36
```

Bitstream identity, timing and utilisation for each milestone are in the private artifact repository
(`zynq-sdr-course-artifacts`) with generated, verified manifests. The shipped differential image:
raw `system_top.bit` sha256 `69023a2b…`, WNS +0.036 ns, 176 DSPs.

## Report checklist

- [x] All figures/artifacts referenced.
- [x] All metrics have units.
- [x] Metadata attached (JSON results, bitstream hashes, commits).
- [x] Commands are reproducible.
- [x] Limitations stated honestly (differential penalty, cold-reset, EVM not instrumented).
- [x] The conclusion follows from measured data.

## Engineering conclusion

```text
The final SDR project achieved a working in-fabric QPSK modem validated on a two-board 915 MHz RF
link. The residual inter-board frequency error was ~200-300 Hz (tracked; ±60 kHz range), the RX
decision margin stayed positive on every axis (~0.97 median normalised), and the payload BER was
4.5e-4 over the RF link and < 5.3e-7 in the coherent fabric loopback. The project MEETS the success
criteria: the chain recovers a known frame deterministically, the whole-burst rotation failures are
eliminated by differential coding plus a lengthened preamble, and every result is reproducible from
committed scripts.
```

**Next steps:** chase the residual differential single-bit rate only if a specific application needs
it (inherent ~3 dB penalty); otherwise the link is complete. Block 12 packages this into the final
course projects.
