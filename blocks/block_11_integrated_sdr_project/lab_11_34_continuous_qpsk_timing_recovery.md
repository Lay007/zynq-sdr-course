# Lab 11.34 — Continuous QPSK Gardner timing recovery

## Goal

Replace the burst-only fixed-phase sampler with a continuous timing loop that can follow
sample-clock mismatch, while retaining a runtime-selectable baseline in the same bitstream.
This lab deliberately stops before claiming a hardware improvement: the boards are offline,
so the current result is an implementation-qualified candidate plus a written live A/B gate.

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

The accepted Lab 11.33 boot image is not overwritten. The Gardner image remains a candidate
until the live protocol below passes.

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

The fresh implementation of the registered boundary closes the physical gate:

- `WNS=+0.049 ns`, `TNS=0.000 ns`;
- `WHS=+0.031 ns`, `THS=0.000 ns`;
- all 77,346 routable nets are fully routed, with zero routing errors;
- utilization is 34,314 LUTs (64.50%), 40,641 registers (38.20%), 8 BRAM tiles (5.71%),
  and 192 DSP48E1s (87.27%);
- bit generation completed with zero errors and zero critical warnings.

The candidate remains isolated under
`tmp/snapshot_impl_sweep/lab1134_registered_netdelay/system_top.bit` instead of replacing the
board-qualified canonical image. Its SHA-256 is
`b7086465dba213544c5a4c558c6deeafb93cca3b8cefa9e41bb3e494b2984b9c`. Physical closure
qualifies the image for the live A/B; it does not prove an RF benefit.

## Live two-board A/B protocol (pending)

When the stand is available again:

1. Keep board A on the proven vendor cyclic-DMA transmitter and board B on the candidate
   course receiver; use the same 915 MHz conducted path, 30 dB attenuator, −30 dB TX and
   +50 dB RX settings as Labs 11.32–11.33.
2. At +30 kHz injected CFO, run an equal budget of 10 attempts at each offset 0…7 with
   `gp_ctrl[14]=0`, then repeat with bit 14 set. No-lock remains in the denominator.
3. Repeat the 0…55 kHz CFO sweep with three attempts per offset and timing mode.
4. Save raw per-attempt rows, `mu/omega`, TED error, bitstream SHA-256, repository commit,
   board roles, and RF settings in the JSON result.
5. Accept Gardner only if it improves the clean-attempt confidence interval without reducing
   full-frame lock rate, then run a longer fixed-condition BER campaign and check for cycle
   slips. A replay or timing-closure win alone is not sufficient.

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
attempt in the reported lock and clean-frame rates.

Until that experiment is complete, the honest conclusion is: **continuous QPSK timing
recovery is implemented, model/RTL qualified, and timing-closed; its live-RF benefit is not
yet measured.**
