# Lab 11.15 - Runtime `bridge_rx_only` witness using stock TX and gpreg RX counters

## Objective

Determine whether the runtime RX path inside the course PL overlay can observe
any samples when the stock AD9361 host TX path is used as the signal source.

The lab separates two possible failure modes that look identical in earlier logs:

1. the overlay bitstream is loaded correctly and `axi_gpreg` answers, but the PL
   RX chain never increments `rx_valid_count` regardless of what drives TX;
2. the PL RX chain increments `rx_valid_count` when a known-good host TX drives
   the link, but was starved earlier because the course PL TX also was broken.

Using the stock host TX as a witness eliminates the second ambiguity.

## Background terms

- `bridge_rx_only`: a `bridge_txrx_mux` overlay variant where TX is strapped to
  a constant and only the RX datapath from the AD9361 is wired into the PL BPSK
  chain, removing PL TX as a variable.
- `host TX`: the stock AD9361 DMA TX path driven directly from the Linux host
  over network IIO — the same cyclic-BPSK burst used in Lab 11.14.
- `gpreg RX counters`: `rx_valid_count` and `received_bits` inside `axi_gpreg`
  at `0x79040000`; non-zero means the PL framer actually processed symbols.
- `rx_common re-init`: an optional write to the AD9361 RX common control
  register to re-arm the DMA path before capture; controlled by `--rx-common-reinit`.

## Files

| Path | Purpose |
|---|---|
| `blocks/block_11_integrated_sdr_project/python/lab_11_15_runtime_bridge_rx_host_tx_probe.py` | load `bridge_rx_only` overlay, run stock host TX, poll gpreg RX counters |
| `blocks/block_11_integrated_sdr_project/python/runtime_rx_common.py` | shared helper to force RX common control register re-init |

## Run

```bash
python blocks/block_11_integrated_sdr_project/python/lab_11_15_runtime_bridge_rx_host_tx_probe.py \
  --bit-bin tmp/bridge_rx_only.wordswap.bit.bin \
  --run-tag live_witness
```

The script:

1. uploads and loads `bridge_rx_only.wordswap.bit.bin` through Linux `fpga_manager`;
2. probes `axi_gpreg` ID/signature to confirm the overlay is alive;
3. configures the stock AD9361 RX path at 915 MHz / 3.84 MS/s;
4. optionally forces `rx_common` re-init if `--rx-common-reinit` is given;
5. starts a cyclic BPSK burst from the host TX path;
6. polls `rx_valid_count` and `received_bits` up to `--poll-limit` times;
7. stops TX, restores AD9361 state, optionally reboots;
8. saves a JSON evidence file with all counter snapshots and timing.

## Safe first settings (checked-in defaults)

| Parameter | Default |
|---|---|
| Center frequency | 915 MHz |
| Sample rate | 3.84 MS/s |
| RF bandwidth | 2 MHz |
| TX attenuation | -50 dB |
| RX gain | 35 dB |
| Poll limit | 128 |
| Poll delay | 20 ms |
| `start_offset` | 62 |

## Interpreting the result

| `rx_valid_count` after TX | Meaning |
|---|---|
| remains 0 | PL RX chain is not receiving samples — overlay or DMAC issue |
| increments | PL RX chain is alive; previous failure was PL TX starvation |

If `rx_valid_count` stays zero even with a confirmed host TX burst, the blocker
is inside the `bridge_rx_only` RX datapath or the AD9361→PL interface, not in
the BPSK modem TX logic.

## Evidence collected on 2026-06-23

The `bridge_rx_only` witness run showed `rx_valid_count = 0` after both a plain
overlay reload and after an `rx_common` re-init attempt, while the host stock TX
was confirmed to be transmitting the BPSK cyclic burst. This proved that the PL
RX path itself does not receive samples from the AD9361 under the runtime
overlay — irrespective of what generates the RF signal.

Next step: investigate whether the AD9361 → PL sample bus (LVDS or parallel)
is properly re-armed after a hot `fpga_manager` reload.

## Report checklist

- [ ] Record `axi_gpreg` ID value (confirm 0x4250534B).
- [ ] Record `tx_valid_count`, `rx_valid_count`, `received_bits` after each poll.
- [ ] Note whether `rx_common` re-init changed the counter trajectory.
- [ ] Attach `dmesg` tail.
- [ ] Confirm host TX was transmitting (BER = 0 from a stock-shell self-check).

## Engineering conclusion template

```text
The runtime bridge_rx_only overlay loaded and axi_gpreg ID = 0x____.
After ____ poll cycles with stock host TX active at ____ MHz,
rx_valid_count = ____ and received_bits = ____.
RX common re-init was / was not attempted; it did / did not change the result.
Conclusion: the PL RX path is / is not receiving AD9361 samples under the
runtime overlay because ______.
```
