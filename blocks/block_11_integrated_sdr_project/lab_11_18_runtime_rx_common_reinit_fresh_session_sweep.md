# Lab 11.18 - Fresh-session runtime sweep after RX common re-init

## Objective

Test whether starting each overlay iteration in a completely fresh SSH session
— rather than reusing persistent connections — changes the `rx_valid_count`
result, and sweep several combinations of `start_offset` and `rx_common_ctrl`
value in that fresh-session mode.

Labs 11.16 and 11.17 reused paramiko SSH connections across iterations.
There is a possibility that a leftover IIO or SSH state from a previous
iteration poisons the next one. This lab controls for that by opening a
fresh SSH connection (and fresh `iio.Context`) at the start of every iteration.

## Sweep design

The script sweeps a configurable grid of:

- `start_offset` values (default: 0, 31, 62, 93, 127);
- `rx_common_ctrl` values (default: 0x70000000, 0x70000001, 0x70000003).

For each combination, a fresh paramiko session is created, the overlay is
reloaded, the AD9361 is configured, `rx_common_ctrl` is written, the host TX
burst is started, and `rx_valid_count` / `received_bits` are polled.

Each iteration ends by rebooting the board back to the stock shell before the
next combination is attempted, guaranteeing a clean start state.

## Files

| Path | Purpose |
|---|---|
| `blocks/block_11_integrated_sdr_project/python/lab_11_18_runtime_rx_common_reinit_fresh_session_sweep.py` | fresh-session grid sweep, JSON results |

## Run

```bash
python blocks/block_11_integrated_sdr_project/python/\
lab_11_18_runtime_rx_common_reinit_fresh_session_sweep.py \
  --bit-bin tmp/bridge_rx_only.wordswap.bit.bin \
  --start-offsets 0,31,62,93,127 \
  --rx-common-ctrl-values 0x70000000,0x70000001,0x70000003 \
  --json-out docs/assets/lab118_fresh_session_sweep_live.json
```

A full 5×3 = 15-point sweep with reboot between iterations takes approximately
30–45 minutes.

## Expected outputs

| File | Content |
|---|---|
| `docs/assets/lab118_fresh_session_sweep_live.json` | per-combination counter results |
| Console summary | any `(start_offset, rx_common_ctrl)` pair with `rx_valid_count > 0` |

## Interpreting the result

| Outcome | Interpretation |
|---|---|
| Some combination yields `rx_valid_count > 0` | connection state was a factor; use the winning combination |
| All combinations yield `rx_valid_count = 0` | the starvation is in hardware or the bitstream, not in host session state |

## Live result on 2026-06-23

All tested combinations produced `rx_valid_count = 0`. The fresh-session
isolation did not change the outcome from Labs 11.16 and 11.17. The evidence
now strongly indicates that the root cause is within the `bridge_rx_only`
bitstream or the AD9361 → PL interface configuration, not in the host-side
software state or the `start_offset` / `rx_common_ctrl` parameter choices.

The next diagnostic step moved to external RF observation (Labs 11.20–11.23)
to verify whether the TX path at least radiates correctly while the RX bring-up
continues in parallel.

## Report checklist

- [ ] State the grid dimensions (start_offset values × rx_common_ctrl values).
- [ ] Attach the JSON sweep file.
- [ ] Note any combination with `rx_valid_count > 0`.
- [ ] Confirm that each iteration started from a stock-shell reboot.

## Engineering conclusion template

```text
A fresh-session sweep over ____ (start_offset, rx_common_ctrl) combinations was
completed. Each iteration started from a stock-shell reboot. rx_valid_count > 0
was observed for combinations: ____ (or "none"). The fresh-session isolation did /
did not change the outcome because ______.
```
