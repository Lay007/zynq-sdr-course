# Lab 11.34 — Continuous QPSK Gardner timing recovery

## Goal

Replace the burst-only fixed-phase sampler with a continuous timing loop that can follow
sample-clock mismatch, while retaining a runtime-selectable baseline in the same bitstream.
The live experiment is now complete. It demonstrates a large lock-rate gain, but the
predeclared clean-attempt gate does not pass over the full CFO sweep, so the fixed sampler
remains the default rather than turning a near-tie into a success claim.

## Why a loop, after Lab 11.33 rejected a timing change

Lab 11.33 disproved one narrow hypothesis: timing walk inside a 140-symbol retained frame was
not the immediate cause of the observed failure. It did not make a fixed sample phase a sound
long-duration receiver. A feedforward picker chooses one of eight phases once; independent
sample clocks continue to move after that choice. The new block therefore estimates timing
error continuously and adjusts a fractional sampling phase instead of periodically choosing a
new integer tap.

## Architecture

`qpsk_symbol_timing_recovery.v` implements a complex sign-Gardner loop:

1. A Q16 modulo-one NCO produces two interpolation strobes per symbol.
2. A linear interpolator forms the sample at the fractional phase between adjacent matched-
   filter samples.
3. Even strobes are on-time symbol outputs; odd strobes are mid-symbol samples.
4. The timing-error detector combines both axes:

   `e = sign(sign(I_mid) * sign(I_now - I_prev) + sign(Q_mid) * sign(Q_now - Q_prev))`

5. A PI loop updates `omega`, with explicit clamps around the nominal `2/SPS` step.

The first hardware candidate used `K1=1/256` and `K2=1/4096`. Its live debug telemetry
showed `omega_q16` spanning 15,600...16,848 around the nominal 16,384, much more movement
than the physical sample-clock mismatch requires. The retuned candidate halves both gains to
`K1=1/512` and `K2=1/8192`; it keeps the model's zero-error drift cases and narrows the live
full-sweep range to 16,088...16,672.

The detector is deliberately amplitude-independent and contains no general divider. With
`SPS=8`, `mu/omega` reduces to the bounded fixed-point operation used by both the Python model
and RTL. The model mirrors Verilog nonblocking semantics: an `omega` update affects the NCO on
the following valid input sample, not the current edge.

## Runtime contract

The bridge compiles both timing methods and selects them with `gp_ctrl[14]`:

| `gp_ctrl[14]` | Timing path | Phase picker |
|---:|---|---|
| 0 | legacy fixed-phase sampler | available through its existing enable |
| 1 | continuous Gardner loop | forced to bypass |

While bit 14 is set, `gp_adc_input_debug` exposes `{omega[15:0], mu[15:0]}` and the capture
debug word exposes the signed three-level TED error. The runtime mux is followed by one
registered valid/I/Q boundary. That register is functionally a uniform one-clock delay and
physically prevents the synchronized control bit from feeding through the mux and two
coarse-CFO DSP levels in one 8 ns divide-select cycle.

The accepted Lab 11.33 behavior remains the runtime default. Gardner is still selectable for
diagnostics and follow-up experiments, but the live result below does not promote it.

## Floating-point and fixed-point evidence

Run the executable model:

```powershell
python blocks/block_05_fpga_hdl_flow/python/qpsk_timing_recovery_model.py
```

For the 140-symbol course frame, the best start-offset sweep produced:

| Observed samples/symbol | Float Gardner errors | Fixed Gardner errors | Fixed-phase errors |
|---:|---:|---:|---:|
| 8.000 | 0 | 0 | 0 |
| 8.030 | 0 | 0 | 0 |
| 8.060 | 0 | 0 | 14 |
| 7.970 | 0 | 0 | 0 |
| 7.940 | 0 | 0 | 12 |

The intentionally large short-frame mismatch makes the failure visible without a long
simulation. A separate 12,000-symbol test uses a realistic ±100 ppm sample-clock mismatch:

| Observed samples/symbol | Fixed Gardner | Best fixed phase |
|---:|---:|---:|
| 8.0008 (+100 ppm) | 0 / 12,000 symbol errors | 1,790 / 12,000 |
| 7.9992 (−100 ppm) | 0 / 12,000 symbol errors | 1,789 / 12,000 |

This is the distinction the old picker cannot erase: it can find a good initial phase, but it
cannot follow the accumulated clock error.

## RTL evidence

The canonical smoke runner now generates vectors and exercises four new benches:

```powershell
python tools/run_block5_hdl_smoke.py `
  --test tb_qpsk_symbol_timing_recovery `
  --test tb_qpsk_timing_recovery_chain `
  --test tb_qpsk_timing_recovery_mux `
  --test tb_qpsk_timing_recovery_retained
```

Current results:

- the standalone RTL block is bit-exact against the integer model for 140 symbols at
  `SPS=8.06`, with zero sample mismatches;
- the full drifted chain recovers 0/280 bit errors, while the fixed sampler has 15/280;
- the runtime mux preserves the same 0/280 versus 15/280 comparison;
- on the retained two-board +30 kHz capture, Gardner preserves the known clean result at
  offsets 3, 4, and 7; the full legacy QPSK top and bridge loopback remain BER=0.

## Physical implementation gate

The first implementation exposed an XDC coverage error, not an algorithmic failure. The
existing timing-recovery multicycle matched only the BPSK hierarchy, leaving the new QPSK
recurrence single-cycle. Its worst path was 24.836 ns and failed the 8 ns divide-select clock
by 17.340 ns. Extending the same setup/hold 4/3 constraint to the QPSK hierarchy removed that
false single-cycle requirement.

The next route reached `WNS=-0.188 ns`, `TNS=-6.084 ns`, with clean hold timing. Its worst path
was no longer the Gardner recurrence; it ran from synchronized `gp_ctrl[14]` through the
runtime mux into the coarse-CFO DSP datapath. Post-route physical optimization improved only
0.002 ns, so the mux output was registered instead of weakening the timing constraints.

The first registered candidate closed the physical gate at `WNS=+0.049 ns` and was used to
discover excessive live loop movement. After retuning the PI gains, a fresh implementation
plus post-route physical optimization closes the final candidate:

- `WNS=+0.003 ns`, `TNS=0.000 ns`;
- `WHS=+0.041 ns`, `THS=0.000 ns`;
- all 77,389 routable nets are fully routed, with zero routing errors;
- bit generation completed with zero errors and zero critical warnings.

The tested raw boot image is
`tmp/snapshot_impl_sweep/lab1134_retuned_postroute/system_top.bit`; its SHA-256 is
`2493b26225b76768ccff985359570761a424a0b6522a70ef4d7e111bbc5ef380`.
It clean-boots board B, probes the AD9361 successfully, and reports the expected course core
ID `0x4250534B`.

## Live two-board A/B result

The conducted stand used board A as the vendor cyclic-DMA transmitter and board B as the
course receiver at 915 MHz through the 30 dB attenuator, with TX at −30 dB and RX at +50 dB.
Both modes used the same bitstream, CFO grid, offsets and retry budget; no-lock attempts stayed
in the denominator.

| Campaign | Mode | Full frames | BER=0 attempts | Aggregate BER in full frames |
|---|---|---:|---:|---:|
| +30 kHz, 80 attempts | fixed | 54/80 (67.5%) | 21/80 (26.25%) | 0.192196 |
| +30 kHz, 80 attempts | retuned Gardner | 72/80 (90.0%) | 22/80 (27.5%) | 0.106597 |
| 0…55 kHz, 288 attempts | fixed | 193/288 (67.01%) | 72/288 (25.00%) | 0.137435 |
| 0…55 kHz, 288 attempts | retuned Gardner | 246/288 (85.42%) | 71/288 (24.65%) | 0.119178 |

The focused +30 kHz gate passes: Gardner improves clean attempts by one and adds 18 full
frames. The larger sweep is the decisive check. Gardner reaches BER=0 at all 12 CFO points
and adds 53 full frames, but produces one fewer clean attempt than fixed sampling. Under the
predeclared point-estimate rule (`clean_rate_improved && lock_rate_preserved`), that is a
reject. The difference is too small to infer that Gardner is intrinsically worse, but it is
also not evidence for replacing the baseline. A longer, higher-power comparison would be a
new experiment with a statistical margin, not a reinterpretation of this one.

The Lab 11.32 hardware runner now has a `--timing-recovery` switch, so the two campaigns use
the same acquisition code and differ only by `gp_ctrl[14]`. Assemble the evidence with the
Lab 11.34 post-processor:

```powershell
python blocks/block_11_integrated_sdr_project/python/lab_11_32_two_board_fabric_coarse_cfo.py `
  --json-out tmp/lab1134_fixed.json
python blocks/block_11_integrated_sdr_project/python/lab_11_32_two_board_fabric_coarse_cfo.py `
  --timing-recovery --json-out tmp/lab1134_gardner.json
python blocks/block_11_integrated_sdr_project/python/lab_11_34_continuous_qpsk_timing_recovery.py `
  --baseline tmp/lab1134_fixed.json --gardner tmp/lab1134_gardner.json
```

The post-processor rejects mismatched CFO grids, offsets, or retry budgets and keeps every
attempt in the reported lock and clean-frame rates. Raw attempts, timing telemetry and the
comparison plots are stored in `docs/assets/lab1134_*_live_20260721.*`.

The honest conclusion is: **continuous QPSK timing recovery is implemented, model/RTL
qualified, timing-closed and measured on the live conducted link. It substantially improves
full-frame lock, but does not pass the full-sweep clean-attempt acceptance gate, so the fixed
sampler remains the default pending stronger evidence.**
