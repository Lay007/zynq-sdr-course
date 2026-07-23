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
90/98% figures are span coverage (`first ≤ 189 ≤ last`) and therefore weaker.

**The obvious mechanism was then tested and refuted.** The natural explanation — ISI from that
run-then-transition pattern leaving symbol 106's Q sample near zero, with the Gardner instant
pushing it across — is computable offline, because the frame and the course RRC are both
deterministic. A matched RRC pair is Nyquist, so at the ideal instant every decision carries full
margin (verified: all 280 bits correct, min |Q| 0.972 of nominal, symbol 106 at 0.976 against a
frame median of 0.998 — unremarkable). ISI only appears once the sampler moves, so the meaningful
ranking is which bit flips at the smallest perturbation:

| Perturbation | First payload bits to flip | Bit 189 |
|---|---|---|
| Timing offset | 70, 22, 68, 135, 137 at 2.69–2.71 samples (≈0.34 symbol) | never flips inside ±0.5 symbol (rank 121 of the 124 that flip at all) |
| Carrier phase | 74, 244, 24, 28, 251 at 43.60–43.85° | 44.15° — rank 14 of 256, i.e. unremarkable |
| Timing × phase grid | 89 (19 points), 68 (17), 24, 88, 137 are the sole failing bit | **0 grid points** |

Carrier phase does not discriminate at all: every one of the 256 payload bits flips inside a
roughly 43.6–45° band around QPSK's theoretical boundary, so no bit is singled out by phase and
bit 189 sits unremarkably inside that band. Timing does discriminate, and it exonerates bit 189 —
it survives to the half-symbol boundary while bits 70, 22 and 68 flip at a third of a symbol. Most
decisive is the combined grid: bit 189 is the sole failing bit at **zero** grid points, while bits
89 and 68 are the sole failure at 19 and 17. Live, that same bit takes 37 of 40 single-bit misses.
The transmitted waveform under timing and carrier error therefore does **not** explain the
observation, and the ISI hypothesis is withdrawn.

The computation is in `blocks/block_11_integrated_sdr_project/python/frame_bit_timing_sensitivity.py`
and needs no hardware.

Two further facts bound the search. The fabric loopback (same modem, same reference, no RF) decodes
the frame with `payload_errors=0` and clean position sentinels, so the frame ROM, the BER counter
and the position encoding are sound. And the RF path differs from that loopback in exactly two
respects: the transmitter is the host-streamed waveform rather than the fabric modulator, and the
signal traverses the AD9361 receive chain (DC block, coarse CFO, Costas, phase picker). The cause
lies in one of those, not in the frame data or the channel geometry.

### What the AD9361 actually delivered

The bridge already records `core_rx` into a 4096-sample BRAM on every burst, readable over gpreg
(`gp_ctrl[7]=1`, address in `gp_start_offset`, `{rx_i, rx_q}` out of `gp_capture_debug`), which is
precisely the "see what the analog chain delivers versus the known-perfect TX" hook. Two method
traps are worth recording, because both produced confident nonsense first:

- the frame lands at a *varying* offset inside the buffer (measured starts 844, 917, 2649, 2876), so
  a short readout window simply misses it — the whole 4096 samples must be read, and a 1536-sample
  window produced `|corr| ≈ 2` "alignments" with absurd multi-kHz frequency fits;
- estimating CFO per alignment candidate *before* correlating is worse than correlating first and
  then fitting the phase line: over 140 symbols the 4th-power estimate is noisy enough to destroy
  the correlation at the true start, and a wrong start then wins.

With the whole buffer read and correlate-then-fit alignment, every frame instance locks cleanly at
`|corr| ≈ 11.7` with a CFO of −300…−410 Hz, matching the known intrinsic inter-board offset. For a
burst whose on-chip telemetry reported exactly one payload error at bit 189:

| Capture | Instance | `|corr|` | CFO | Host decision errors | Symbol 106 Q margin |
|---|---|---:|---:|---:|---:|
| failing burst | start 844 | 11.66 | −305.9 Hz | 0 | +0.725 (rank 94/140) |
| failing burst | start 2876 | 11.38 | −411.7 Hz | 2 (both elsewhere) | +0.741 (rank 114/140) |
| clean burst | start 917 | 11.66 | −301.9 Hz | 0 | +0.674 (rank 37/140) |
| clean burst | start 2649 | 11.65 | −299.1 Hz | 0 | +0.710 (rank 75/140) |

Symbol 106's Q decision is healthy in every instance — always positive, between +0.67 and +1.16,
sitting mid-to-upper in the frame's margin ranking (median ≈ +0.71). Even in the one instance where
the host decoder does make two errors, symbol 106 is not among them. The signal the AD9361 delivered
therefore contains no marginal decision at that symbol.

The honest caveat is that the host decoder is idealised — data-aided alignment plus a linear phase
fit — and therefore more capable than the causal on-chip Costas and fixed sampler, so the chip can
certainly err where this decoder does not. But a merely weaker receiver should fail at the *weakest*
decisions, and those are other symbols entirely. A healthy, mid-ranked decision being reported as
the single error points at the receiver's own processing, or at how the error index is attributed,
rather than at signal quality. Note also that the position index has only ever been exercised with a
real error on the RF path: the fabric loopback never produces one, so hardware validation of the
index itself rests on the RF-path numbers it is being used to interpret.

### The failure does not move

Two cheap invariance checks close the analog branch entirely. Frame alignment does not move it: in
the 160-pair campaign the single-bit error sits at index 189 at **all eight** start offsets (Gardner
0–7, fixed at 0, 5 and 7). Neither does the carrier — re-running 100 Gardner bursts at each of three
frequencies leaves the distribution untouched:

| Carrier | Locked | Dirty | Single-bit frames | Indices | Bit 189 share |
|---|---:|---:|---:|---|---:|
| 910 MHz | 100/100 | 90 | 30 | 189 × 30 | 100% |
| 915 MHz | 100/100 | 89 | 27 | 189 × 26, 2 × 1 | 96% |
| 920 MHz | 99/100 | 87 | 31 | 189 × 30, 2 × 1 | 97% |

Changing the carrier changes the LO, the DC offset, the filter response and the AGC operating point
while leaving the frame data and the bit indexing untouched, and the failure is indifferent to all
of it. Together with the capture measurement — a healthy, mid-ranked decision margin at that symbol
— the analog path, the channel and the frame alignment are all excluded. The defect is locked to the
data or to the index, which leaves exactly one fork: either the on-chip decoder genuinely gets bit
189 wrong for a deterministic reason, or the reported index is not the bit that actually failed.

### Asking the decoder directly

That fork was unanswerable rather than merely unanswered: the bridge hard-wires its recovered-bit
debug to zero in QPSK mode, so the QPSK path had no decoded-bit visibility at all. `gp_ctrl[16]` now
exports it — every recovered dibit shifts into a 288-bit register that freezes when the burst
completes, read back as nine words plus a bit count (see `decoded_bit_readout.py` and
`lab_11_40_resolve_decoded_bit_index.py`).

Two implementation choices are load-bearing. A shift register rather than an addressed write,
because an address decode in the `sample_clk` domain was unaffordable at a +0.020 ns margin. And a
freeze at the *end* of the burst rather than a capture from its start, because the sampler emits
`RX_SAMPLE_MARGIN`=256 extra symbols and the frame-sync finds the frame somewhere inside that
stream — the first 288 bits are pre-frame noise.

The comparison also needs care. The BER counter does **not** compare raw dibits to the ROM: it runs
two frame-sync branches (A emits `{d0,d1}`, B the 90° de-rotation `{d1,~d0}`) and each resolves its
own 180° ambiguity, so four constellation rotations are possible while the readout captures the raw
dibits. Comparing only the identity made 7 of 10 bursts look half-wrong (121–129 mismatches, the
signature of a wrong comparison rather than a broken decoder); trying all four rotations turned
3/10 into 10/10, and all four occurred in practice (A ×3, A+invert ×2, B ×1, B+invert ×4).

The result is unambiguous. Across **10 of 10** bursts whose telemetry reported a single payload
error at index 189, the decoded frame disagrees with the ROM at exactly one bit — frame bit 213,
which is payload bit 189 — and at no other bit. Three clean frames disagree nowhere.

**The position telemetry is correct, and the receiver really does produce a wrong bit at symbol
106's Q axis.** Note the index bases differ by the preamble length: the alignment returns FRAME bit
indices, so frame bit 213 *is* payload bit 189 — comparing the two directly once produced a verdict
exactly opposite to the data.

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

The obvious mechanism has already been tested and withdrawn: offline, on the deterministic frame and
RRC, bit 189 never flips inside ±0.5 symbol of timing error (while bits 70, 22 and 68 flip at a
third of a symbol), and it is the sole failing bit at zero points of a timing × phase grid where
bits 89 and 68 fail at 19 and 17 points. Carrier phase discriminates nothing — all 256 payload bits
flip within a ~43.6–45° band around QPSK's boundary. The transmitted waveform under timing and
carrier error does not explain the live result.

The remaining fork has since been closed by reading the decoder's own output (`gp_ctrl[16]`): across
10 of 10 flagged bursts the decoded frame differs from the ROM at exactly frame bit 213 — payload
bit 189 — and nowhere else, while clean frames differ nowhere. The position telemetry is correct and
the receiver genuinely produces a wrong bit at symbol 106's Q axis.

So the target is now narrow and reproducible: a deterministic wrong decision on one symbol whose
delivered margin is healthy, invariant to start offset and carrier, with the frame ROM, BER counter
and index encoding all exonerated. What remains is the path between a good sample and a bad decision
— Costas, the sampler, the hard decision. Still no PI-gain sweep is justified: the defect is
deterministic, and a deterministic defect has a cause rather than a tuning.

Carried by the timing-clean image `SHA-256 2d7ed04d…` (`WNS=+0.020 ns`); the host now refuses to
report positions from an image that does not implement them, so this class of result cannot be faked
by a stale bitstream again.
