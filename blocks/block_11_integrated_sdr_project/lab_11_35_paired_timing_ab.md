# Lab 11.35 — Paired timing A/B and carrier-rotation-invariant Gardner TED

Lab 11.34 left an ambiguous result: the continuous Gardner path acquired many more full
frames, but finished one clean attempt behind the fixed sampler in a 288-attempt sweep. This
lab increases statistical power, removes slow bench drift from the comparison, and uses the
result to diagnose a carrier-phase defect in the first detector.

## Conducted setup and safety contract

The live setup is fixed throughout the experiment:

- board A: vendor cyclic-DMA transmitter, TX1;
- board B: course receiver, RX1;
- RF path: `A TX1 -> 30 dB attenuator -> B RX1`;
- carrier: 915 MHz; TX gain: -30 dB; RX gain: +50 dB;
- both timing modes run in the same bitstream and differ only by `gp_ctrl[14]`;
- both transmit channels are forced to -89.75 dB before acquisition and in a `finally` path.

This is a conducted-only procedure. Do not run it without the attenuator and verified port
direction.

## Why the comparison is paired

The Lab 11.35 runner observes fixed and Gardner modes as a pair at the same injected CFO and
start offset. Pair order alternates `AB`, `BA`, so a slow RF or thermal drift cannot
systematically favour the mode that always runs first.

The gate is declared before acquisition. Let `delta` mean Gardner minus fixed:

- lower 95% confidence bound for clean-attempt `delta` must be at least -2 percentage points;
- lower 95% confidence bound for full-frame-lock `delta` must be at least +10 percentage
  points.

Every no-lock attempt remains in the denominator. The interval is computed from discordant
pairs, which are the observations that contain information about the mode difference.

Run the complete campaign with:

```powershell
python blocks/block_11_integrated_sdr_project/python/lab_11_35_paired_timing_ab.py `
  --cfo-values 0,30000,55000 `
  --offsets 0,1,2,3,4,5,6,7 `
  --pairs-per-offset 50 `
  --json-out docs/assets/lab1135_paired_timing_ab_live_20260721.json `
  --png-out docs/assets/lab1135_paired_timing_ab_live_20260721.png
```

The runner checkpoints the full per-attempt JSON during acquisition and rejects an
incompatible resume. It records bitstream SHA-256, repository revision, RF settings, order,
mode telemetry and the predeclared margins.

## Paired result for the axis-sign detector

The campaign contains 1,200 pairs, or 2,400 receiver attempts:

| Metric | Fixed | Axis-sign Gardner | Paired delta | 95% confidence interval |
|---|---:|---:|---:|---:|
| Full-frame lock | 774/1,200 (64.50%) | 928/1,200 (77.33%) | +12.83 pp | +9.27…+16.40 pp |
| BER=0 attempt | 292/1,200 (24.33%) | 274/1,200 (22.83%) | -1.50 pp | -4.97…+1.97 pp |

The point estimates satisfy both margins, but the lower confidence bounds do not. The
candidate therefore remains unpromoted. This is not evidence that Gardner is generally
worse: it is a statistically honest inconclusive result under the declared gate.

The aggregate numbers hide the useful clue:

| Injected CFO | Fixed BER=0 | Axis-sign Gardner BER=0 | Clean delta | Lock delta |
|---:|---:|---:|---:|---:|
| 0 Hz | 118/400 | 12/400 | -26.50 pp | +10.25 pp |
| +30 kHz | 93/400 | 109/400 | +4.00 pp | +13.50 pp |
| +55 kHz | 81/400 | 153/400 | +18.00 pp | +14.75 pp |

At zero CFO the loop often reports a full frame, but only 12/400 attempts are clean. With a
rotating carrier the same loop improves continuously. Timing recovery should not acquire
better merely because residual carrier rotation dithers the I/Q axes, so this CFO dependence
points at the detector rather than at the PI tuning.

## Root cause

The first multiplier-free approximation used independent signs on I and Q:

```text
e_old = sign(sign(I_mid) * sign(I_now - I_prev)
           + sign(Q_mid) * sign(Q_now - Q_prev))
```

It is inexpensive, but it is not invariant to a common rotation of the constellation. A
static carrier phase changes the frequency of axis ties and therefore changes detector gain.
Residual CFO masks the defect by sweeping the constellation through many orientations.

The corrected detector uses the sign of the complex-vector dot product:

```text
e_new = sign(I_mid * (I_now - I_prev)
           + Q_mid * (Q_now - Q_prev))
```

For any common orthogonal rotation `R`, `(R a) dot (R b) = a dot b`; the timing decision is
therefore independent of carrier phase. The hardware cost is two DSP multipliers. The PI
output remains ternary, so the downstream loop arithmetic and telemetry contract are
unchanged.

## Model and RTL qualification

The fixed-point model retains the old TED as a regression oracle. On a static carrier-phase
sweep from 0 to 90 degrees, the old detector produces symbol errors while the dot-product
detector remains at zero.

The selected terms are `K1=256/65536` and `K2=3/65536`. Three random 12,000-symbol streams
pass with zero errors at +/-100 ppm and +/-200 ppm sample-clock mismatch for every carrier
phase from 0 to 90 degrees in 5-degree steps. The short +/-0.75% SPS stress cases and the
retained +30 kHz hardware capture also pass.

All 34 canonical HDL smoke tests pass, including standalone bit-exact timing recovery, the
full QPSK chain, runtime mux selection and retained-capture replay.

## Physical implementation

The first route of the dot-product TED ended at `WNS=-7.749 ns`, despite clean hold timing.
The complete path report showed an 8 ns requirement ending at `ted_dot_*_psdsp/D`: Vivado had
materialized a register on a DSP input during placement, after the pre-opt XDC hook had
enumerated ordinary timing-recovery D/R/S pins.

The fix does not increase the multicycle budget. It adds the A/B/C data pins of DSP48 cells
inside only the timing-recovery hierarchy, so the existing setup/hold 4/3 exception follows
the placement transform. Coverage rises from 364 to 1,364 pins. A fresh
`ExtraNetDelay_high / AggressiveExplore / NoTimingRelaxation` implementation closes at:

- `WNS=+0.004 ns`, `TNS=0.000 ns`;
- `WHS=+0.017 ns`, `THS=0.000 ns`;
- 77,638/77,638 routable nets fully routed, zero routing errors;
- bitgen: zero errors and zero critical warnings;
- SHA-256: `907a277cd0906ae228b09414930a6a7e8e56efbbe73e6e56953139f25bd1b80d`.

The placed design still uses 192/220 DSP48E1 blocks: the old Verilog sign products had also
been inferred into two DSPs, so replacing them with the wide dot product changes function and
timing but not the final DSP count.

Board B clean-boots the exact image, initializes AD9361, exposes three IIO devices and returns
course core ID `0x4250534B`.

## Focused zero-CFO result for the corrected TED

The predeclared next step was the point where the original detector collapsed. A 400-pair
zero-CFO run gives:

| Metric | Fixed | Dot-product Gardner | Paired delta | 95% confidence interval |
|---|---:|---:|---:|---:|
| Full-frame lock | 247/400 (61.75%) | 354/400 (88.50%) | +26.75 pp | +21.11…+32.39 pp |
| BER=0 attempt | 108/400 (27.00%) | 11/400 (2.75%) | -24.25 pp | -28.84…-19.66 pp |
| Aggregate BER in full frames | 0.130682 | 0.067645 | — | — |

The rotation-invariant detector greatly improves acquisition and halves aggregate BER, but it
does **not** remove the exact-zero-frame collapse. The carrier-phase diagnosis therefore
identified a real model defect, but not the complete cause of the live clean-frame failure.
The focused gate rejects the candidate, so a three-CFO campaign would not change the promotion
decision and is intentionally not run.

The error distribution contains the next clue:

| Maximum bit errors in a full frame | Fixed frames | Dot-product Gardner frames |
|---:|---:|---:|
| 0 | 108 | 11 |
| 1 | 135 | 117 |
| 2 | 146 | 143 |
| 3 | 157 | 163 |
| 5 | 161 | 202 |
| 10 | 177 | 288 |

The corrected loop often misses exact zero by one bit, yet it overtakes fixed sampling by the
three-error threshold and dominates by five errors. The existing QPSK register map exported
payload errors as a hard-wired zero, so the 400-pair evidence cannot tell whether those
single-bit misses are in the acquisition preamble or the payload.

Lab 11.35 therefore adds real QPSK payload-error telemetry to the already existing low half of
the error-count register. A dedicated RTL test injects one tolerated preamble error and one
payload error and observes `(total=1,payload=0)` and `(total=1,payload=1)` respectively. The
next short hardware run is an instrumentation experiment, not another reinterpretation of the
failed clean gate.

## Live payload localization

The telemetry image required one bounded post-route optimization after the first implementation
ended at `WNS=-0.049 ns`. `AggressiveExplore` improved the same routed checkpoint without changing
RTL or constraints. The image deployed to board B closes at:

- `WNS=+0.009 ns`, `TNS=0.000 ns`;
- `WHS=+0.028 ns`, `THS=0.000 ns`;
- 77,735/77,735 routable nets fully routed, zero routing errors;
- bitgen: zero errors and zero critical warnings;
- SHA-256: `29fb47e06a255ab6829af03d099d09dd29e569e62a9a46a37dfd35941c4527ca`.

A clean boot again reports core ID `0x4250534B`, a successful AD9361 initialization and three
IIO devices. The focused CFO=0 instrumentation run contains 160 interleaved pairs:

| Metric | Fixed | Dot-product Gardner | Paired delta | 95% confidence interval |
|---|---:|---:|---:|---:|
| Full-frame lock | 98/160 (61.25%) | 146/160 (91.25%) | +30.00 pp | +21.00…+39.00 pp |
| BER=0 attempt | 44/160 (27.50%) | 4/160 (2.50%) | -25.00 pp | -32.57…-17.43 pp |
| Aggregate BER in full frames | 0.109803 | 0.068224 | — | — |
| Aggregate payload BER | 0.117985 | 0.073523 | — | — |

The split answers the diagnostic question:

| Full-frame error class | Fixed | Dot-product Gardner |
|---|---:|---:|
| Dirty full frames | 54 | 142 |
| Preamble-only | 3 | 0 |
| Payload-only | 27 | 122 |
| Mixed preamble and payload | 24 | 20 |
| Single-bit dirty frames | 15 | 55 |
| Single bit in preamble | 1 | 0 |
| Single bit in payload | 14 | 55 |

All 55 single-bit Gardner misses are in the payload. The acquisition preamble is therefore not
the source of the exact-zero collapse. Because the payload is longer than the preamble, raw counts
alone would be weak evidence; the more useful comparison is that Gardner payload BER is 0.073523
while preamble BER is only 0.011701. The receiver acquires a good frame start and then loses
decision quality inside the frame.

The next bounded diagnostic is error position within the payload (for example, four segment
counters plus first/last error index). Late clustering would implicate residual timing/carrier
drift; a uniform distribution would point instead at decision margin or noise. Acquisition changes
and another blind PI-gain sweep are not justified by this result.

## Payload error-position telemetry: implemented, timing-clean, live still pending

The predeclared diagnostic is now in the RTL and host and has a timing-clean bitstream. It has
**not yet run on the bench** — the stand is powered down at the time of writing, so this section
separates what is implemented and simulated from what is measured.

**RTL and host — implemented.** With `gp_ctrl[4]=1` and `gp_ctrl[15]=1` the existing register map
carries positional telemetry with no block-design or address-map change, over the 280-bit frame
(24-bit preamble, 256-bit payload, four 64-bit payload quarters):

- `gp_tx_valid_count` = `{quarter3, quarter2, quarter1, quarter0}` — four saturating 8-bit
  payload-quarter error counters;
- `gp_rx_valid_count` = `{last_payload_error_index[15:0], first_payload_error_index[15:0]}`, where
  `0xFFFF` means "no error".

A dedicated bridge test injects errors at known positions and checks the quarter counters and the
first/last sentinels; the host returns `payload_error_position` and aggregates availability, the
four segment sums, and first/last-index statistics. `FIXED_MODE` and `GARDNER_MODE` set
`gp_ctrl[15]`.

**Simulation and regression — passing.** Canonical HDL smoke 34/34; the targeted QPSK
digital-loopback and paired-timing Python tests pass. The RRC transmit FIR was *pipelined rather
than constrained*: its real critical path (delay line → symmetric pair-add → a
placement-materialized DSP input register) does not admit a multicycle exception, because the
internal fabric loopback can present `valid` every cycle, so a false exception would corrupt the
continuous case. The symmetric pre-adds and centre tap are now registered ahead of the multipliers
(FIR latency 9 instead of 8), and the transform is bit-exact over 2,312 vectors.

**Timing-clean build — obtained.** With the FIR path pipelined, the new worst path is not in the
modem at all but in the diagnostic capture peak detector
(`capture_nonzero_seen_* → capture_peak_abs_sample_reg[*]/CE`), a route-heavy telemetry path. A
fresh main-seed implementation closed at `WNS=-0.145 ns`; an `ExtraNetDelay_high` placement from the
vendor post-opt snapshot took it to `WNS=-0.076 ns`; one allowed `AggressiveExplore` post-route
`phys_opt_design` on that routed checkpoint — no RTL or constraint change — closed it:

- `WNS=+0.020 ns`, `TNS=0.000 ns` (0 failing endpoints);
- `WHS=+0.039 ns`, `THS=0.000 ns` (0 failing endpoints);
- 80,546/80,546 routable nets fully routed, zero routing errors;
- bitstream written; SHA-256:
  `2d7ed04d79a180f6d3a4e97fab5a7b52a5d028b7705c04f79ecdac3be0834296`.

The `+0.020 ns` margin is thin and was reached by post-route optimization on a diagnostic path, so
repeat-build/seed stability of this specific closure is the honest caveat; pipelining the peak
detector remains available if a larger, placement-independent margin is wanted. The earlier
pre-telemetry image (`SHA-256 29fb47e0…`, the 160-pair source above) is now **stale** for the
position experiment and must not be reused.

**Live position experiment — measured, and neither predeclared hypothesis was right.**

One guard had to be added first. `gp_ctrl[15]` multiplexes two registers that a *pre-telemetry*
image still drives with their old meaning (a TX sample counter and an RX valid counter), and the
host decoded them unconditionally. Probed against the old image, a clean frame
(`payload_errors=0`) reported `segment_errors=[224,4,0,48]`, `first=1843`, `last=0`, and frames
with 121 and 2 payload errors reported the *same* segment counts — a campaign run in that state
would have produced confident nonsense. `decode_payload_error_position()` now validates against the
frame's own payload error count (the quarter counters cannot saturate, so the four counts must sum
exactly to `payload_errors`, and indices must satisfy `0 ≤ first ≤ last < 256` or both be
sentinels) and returns None otherwise. Verified on the bench: the same probe returns None on the
old image and real sentinels (`[0,0,0,0]`, both indices None) on the new one.

The measured run is 160 interleaved pairs at CFO = 0 on the timing-clean image
(`SHA-256 2d7ed04d…`), eight start offsets × 20 pairs:

| Metric | Fixed | Dot-product Gardner | Paired delta | 95% confidence interval |
|---|---:|---:|---:|---:|
| Full-frame lock | 87/160 (54.38%) | 133/160 (83.13%) | +28.75 pp | +20.17…+37.33 pp |
| BER=0 attempt | 36/160 (22.50%) | 3/160 (1.88%) | −20.62 pp | −27.38…−13.87 pp |
| Aggregate BER in full frames | 0.106568 | 0.068018 | — | — |
| Aggregate payload BER | 0.113820 | 0.073132 | — | — |

The quarter counters do not show the predicted shapes. Neither sampler ramps monotonically toward
the end of the payload, and neither is flat:

| Payload quarter | Fixed | Gardner |
|---|---:|---:|
| q0 (bits 0–63) | 530 (20.9%) | 492 (19.8%) |
| q1 (bits 64–127) | 779 (30.7%) | 529 (21.2%) |
| q2 (bits 128–191) | 713 (28.1%) | 798 (32.0%) |
| q3 (bits 192–255) | 513 (20.2%) | 671 (26.9%) |

The sharp answer is in the single-bit frames, where first and last index coincide with the error
itself:

| Single-payload-bit frames | Fixed | Gardner |
|---|---:|---:|
| Count | 7 | 33 |
| In q0 / q1 / q2 / q3 | 0 / 0 / **7** / 0 | 2 / 0 / **31** / 0 |
| Error index | 173, then **189 × 6** | 2, 2, then **189 × 31** |

**37 of 40 single-bit misses sit at exactly payload bit 189**, independently for both samplers.
That index is frame bit 213, i.e. the **Q axis of QPSK symbol 106** — the last symbol of a
four-symbol Q run before a sign change. Consistently, the aggregate `first_error_index` never
exceeds 189 for either sampler, and the error span covers bit 189 in 90% of fixed dirty frames and
98% of Gardner dirty frames. Frames are effectively bimodal: either completely clean, or wrong at
189.

So the systematic one-bit miss is **not** within-frame drift (no monotonic ramp) and **not** a
uniform decision-margin loss (not flat). It is one symbol decided at the boundary. The honest
strength of the evidence differs by claim: the single-bit localization is direct, while the
90/98% figures are span coverage (`first ≤ 189 ≤ last`) and therefore weaker; the mechanism —
ISI around that particular run-then-transition pattern leaving symbol 106's Q sample near zero, with
the Gardner instant pushing it to the wrong side — is a hypothesis consistent with the bimodality,
not yet a measurement.

This also reinterprets the earlier promotion decision. The clean-frame gate that rejects Gardner is
in large part a proxy for this single bit: Gardner locks far more often (133 vs 87) and carries a
markedly lower payload BER (0.0731 vs 0.1138), yet reaches BER=0 only 3 times in 160 because it
almost always misses bit 189. The gate remains the declared gate and `gp_ctrl[14]=0` remains the
default, but "Gardner cannot produce clean frames" is more precisely "Gardner cannot get symbol 106
right".

Evidence: `docs/assets/lab1135_payload_position_live_20260723.json` (and `.png`).

## Verdict

The dot-product TED is model-correct, timing-clean and hardware-qualified, but fails the focused
clean-frame gate decisively. `gp_ctrl[14]=0` remains the runtime default and the fixed sampler
remains the accepted baseline.

Position telemetry has now answered the question it was built for, and the answer was neither
predeclared option. The systematic one-bit misses are not spread across the payload and do not
accumulate toward its end: 37 of 40 single-bit frames fail at exactly payload bit 189 — the Q axis
of QPSK symbol 106 — for both samplers independently, and frames are bimodal between fully clean
and wrong-at-189. Within-frame drift and uniform decision-margin loss are both rejected; the target
is one symbol decided at the boundary.

That also sharpens what the rejected gate measured. Gardner locks far more often (133/160 vs
87/160) and carries a lower payload BER (0.0731 vs 0.1138), yet reaches BER=0 three times in 160
because it almost always misses that one bit. The gate stands, but the conclusion "Gardner cannot
produce clean frames" is more precisely "Gardner cannot get symbol 106 right".

The next diagnostic is therefore not another PI-gain sweep but the sampled value itself: capture
symbol 106's Q sample under both timing modes and check how close to zero it lands, and whether the
run-then-transition ISI around it explains the boundary. Carried by the timing-clean image
`SHA-256 2d7ed04d…` (`WNS=+0.020 ns`); the host now refuses to report positions from an image that
does not implement them, so this class of result cannot be faked by a stale bitstream again.
