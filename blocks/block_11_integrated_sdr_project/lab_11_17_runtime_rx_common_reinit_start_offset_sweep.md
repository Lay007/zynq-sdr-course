# Lab 11.17 - start_offset sweep after runtime RX common re-init under stock host TX

## Objective

Determine whether the `start_offset` AXI-gpreg parameter is a factor in the
`rx_valid_count = 0` result seen in Lab 11.15.

The `start_offset` field controls how many clock cycles the PL framer waits
after the burst-start trigger before it begins sampling symbols. If the
AD9361 → PL pipeline latency changes between stock and runtime boots, the
originally chosen value (62) may cause the framer to sample outside the valid
window, explaining zero `rx_valid_count` even when the DMA path is healthy.

## Sweep design

The script sweeps `start_offset` from 0 to a configurable upper bound (default
127) in steps of 1. For each value it:

1. reloads the `bridge_rx_only` overlay (fresh per iteration or once at the
   start, controlled by `--reload-per-iter`);
2. optionally forces `rx_common` re-init;
3. starts the stock host TX burst;
4. polls `rx_valid_count` and `received_bits`;
5. records the counter snapshot.

The sweep writes a JSON array with one entry per `start_offset` value, plus
a summary of which values, if any, produced `rx_valid_count > 0`.

## Files

| Path | Purpose |
|---|---|
| `blocks/block_11_integrated_sdr_project/python/lab_11_17_runtime_rx_common_reinit_start_offset_sweep.py` | sweep `start_offset`, collect gpreg counter snapshots, write JSON report |

## Run

```bash
python blocks/block_11_integrated_sdr_project/python/\
lab_11_17_runtime_rx_common_reinit_start_offset_sweep.py \
  --bit-bin tmp/bridge_rx_only.wordswap.bit.bin \
  --start-offset-max 127 \
  --json-out docs/assets/lab117_start_offset_sweep_live.json
```

The full 0–127 sweep takes approximately 5–10 minutes depending on `--poll-limit`
and SSH latency.

## Expected outputs

| File | Content |
|---|---|
| `docs/assets/lab117_start_offset_sweep_live.json` | per-iteration counter snapshots |
| Console summary | first `start_offset` with `rx_valid_count > 0`, or "none found" |

## Interpreting the result

| Outcome | Interpretation |
|---|---|
| Some `start_offset` values give `rx_valid_count > 0` | pipeline latency changed; use the working value in subsequent labs |
| All `start_offset` values give `rx_valid_count = 0` | latency is not the issue; DMA starvation is deeper |
| `rx_valid_count > 0` but `received_bits = 0` | framer clocking works but bit alignment is off — check `rx_decision_mode` |

## Live result on 2026-06-23

The sweep over `start_offset ∈ [0, 127]` produced `rx_valid_count = 0` for
every tested value. This rules out `start_offset` misconfiguration as the root
cause of the RX starvation under the runtime overlay. Combined with the result
from Lab 11.16, the evidence points to a deeper AD9361 → PL DMA path issue
that persists after any single register adjustment.

## Report checklist

- [ ] State the `start_offset` range swept and step size.
- [ ] Attach the JSON sweep file.
- [ ] Note whether any value produced `rx_valid_count > 0`.
- [ ] Record the `rx_common` re-init setting used.
- [ ] State the conclusion about pipeline latency as a factor.

## Engineering conclusion template

```text
start_offset was swept from ____ to ____ in steps of ____ with rx_common reinit
____ (enabled / disabled). rx_valid_count > 0 was observed at start_offset values:
____ (or "none"). Pipeline latency is / is not the primary cause of the
rx_valid_count = 0 result because ______.
```
