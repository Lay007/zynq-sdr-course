# Lab 11.19 - Runtime self-timed `bridge_txrx_mux` bring-up

## Objective

Run the full `bridge_txrx_mux` overlay (TX + RX both wired through the PL
modem) using a self-timed burst-control sequence and determine whether either
`tx_valid_count` or `rx_valid_count` advances when both PL TX and PL RX are
active simultaneously.

Previous labs used `bridge_rx_only` (PL RX only) with the stock host TX as a
witness. This lab returns to the full bidirectional overlay and uses a
self-timed mode where the PL TX starts first, waits a fixed settle time, then
RX polling begins — mimicking a hardware timing controller.

## Why self-timed mode

In the standard burst-control mode, the host sends a start command and
immediately polls `rx_valid_count`. If the PL TX path needs time to prime the
AD9361 DMA pipeline before the RX path becomes active, polling too early always
sees zero. Self-timed mode introduces a configurable TX-settle window before
RX polling begins.

## Files

| Path | Purpose |
|---|---|
| `blocks/block_11_integrated_sdr_project/python/lab_11_19_runtime_bridge_txrx_self_timed_bringup.py` | self-timed full-overlay bring-up, JSON evidence |

## Run

```bash
python blocks/block_11_integrated_sdr_project/python/\
lab_11_19_runtime_bridge_txrx_self_timed_bringup.py \
  --bit-bin tmp/bridge_txrx_mux.wordswap.bit.bin \
  --tx-settle-ms 250 \
  --poll-limit 256 \
  --run-tag self_timed_live
```

## Self-timed sequence

```
load overlay → verify axi_gpreg ID
configure AD9361 (915 MHz / 3.84 MS/s)
assert burst_start
wait tx_settle_ms
↓
poll loop:
  read tx_valid_count, rx_valid_count, received_bits
  if rx_valid_count > 0 or received_bits > 0 → success
  if poll_limit reached → timeout
↓
restore AD9361 → optional reboot
save JSON evidence
```

## Parameter guide

| Parameter | Meaning | Try first |
|---|---|---|
| `--tx-settle-ms` | wait after burst_start before RX polling | 250 ms |
| `--poll-limit` | max RX counter read attempts | 256 |
| `--poll-delay-ms` | pause between polls | 20 ms |
| `--start-offset` | PL framer start offset cycles | 62 |

## Interpreting the result

| Outcome | Meaning |
|---|---|
| `tx_valid_count > 0`, `rx_valid_count > 0` | full bidirectional bring-up successful |
| `tx_valid_count > 0`, `rx_valid_count = 0` | PL TX works; RX starvation persists |
| both zero | TX DMA not primed; check burst_start AXI write |

## Live result on 2026-06-23

Self-timed runs consistently showed `tx_valid_count > 0` (PL TX is live) but
`rx_valid_count = 0` regardless of `tx_settle_ms` values up to 500 ms. This
confirmed that TX priming is not the limiting factor — the RX starvation is
independent of how long TX has been running before RX polling starts.

This result, combined with the evidence from Labs 11.15–11.18, shifted the
investigation toward RTL-SDR external monitoring (Labs 11.20–11.25) to confirm
that the TX signal is actually radiated, while the RX path investigation
continues at the bitstream level.

## Report checklist

- [ ] Record `tx_valid_count` after first poll with `tx_valid_count > 0`.
- [ ] Record `rx_valid_count` and `received_bits` at every poll.
- [ ] State `tx_settle_ms` value used.
- [ ] Attach `dmesg` tail.
- [ ] Compare with Lab 11.15 `bridge_rx_only` result.

## Engineering conclusion template

```text
The self-timed bridge_txrx_mux bring-up ran with tx_settle_ms = ____ ms and
poll_limit = ____. tx_valid_count reached ____ after ____ ms.
rx_valid_count after full poll window: ____. received_bits: ____.
TX priming is / is not the cause of rx_valid_count = 0 because ______.
```
