# Lab 11.16 - RX host capture before and after runtime RX common re-init

## Objective

Find out whether writing to the AD9361 `rx_common_ctrl` register after a
runtime `fpga_manager` overlay reload is enough to restore the `libiio` host
RX capture path.

Lab 11.13 showed that host RX capture works on the clean stock shell but fails
(`errno 110 — Connection timed out`) after the course overlay is hot-loaded.
Lab 11.15 confirmed the PL RX path also stays dark. This lab tests whether a
targeted `rx_common` re-init over SSH can recover the stock host capture path
without a full board reboot.

## Why this matters

A full board reboot takes ~2 minutes and resets the entire overlay state.  If a
single register write can re-arm the `axi_ad9361_adc_dma` DMA without a reboot,
the round-trip for iterative FPGA experiments drops from minutes to seconds.

## Files

| Path | Purpose |
|---|---|
| `blocks/block_11_integrated_sdr_project/python/lab_11_16_runtime_rx_common_reinit_probe.py` | load overlay, attempt host capture, force `rx_common` re-init, attempt capture again, report |
| `blocks/block_11_integrated_sdr_project/python/runtime_rx_common.py` | `force_rx_common_ctrl_request()` — sends the board-side re-init sequence over SSH |

## What the script does

For each stage (pre-reload, post-reload, post-reinit), the script records:

- AD9361 board state snapshot over SSH;
- `axi_ad9361_adc_dma` register state;
- one direct `libiio Buffer.refill()` capture attempt from the host;
- one `iio_readdev` capture attempt;
- `dmesg` tail (last 80 lines).

After the post-reload stage fails (expected), it calls
`force_rx_common_ctrl_request()` and repeats both capture attempts.

## Run

```bash
python blocks/block_11_integrated_sdr_project/python/lab_11_16_runtime_rx_common_reinit_probe.py \
  --bit-bin tmp/bridge_rx_only.wordswap.bit.bin \
  --json-out docs/assets/lab116_runtime_rx_common_reinit_probe_live.json
```

After a successful run the script attempts a board reboot to return the bench
to the stock-shell baseline. Pass `--no-reboot` to skip the reboot.

## Interpreting the result

| Post-reinit capture | Meaning |
|---|---|
| `libiio` succeeds | `rx_common` re-init is sufficient; no reboot needed for iterative tests |
| `libiio` still fails | the DMA starvation is deeper than the `rx_common` register; board reboot required |
| partial recovery | `iio_readdev` works but `libiio` does not — buffer-level difference, investigate `iio_buffer_size` |

## Live result on 2026-06-23

The `rx_common` re-init write (`rx_common_ctrl = 0x70000001` over SSH) did not
restore the host `libiio` capture path. Both `Buffer.refill()` and `iio_readdev`
continued to fail with `errno 110` after the re-init. The DMA starvation
introduced by the runtime overlay reload requires a full board reboot to recover.

This result narrows the remaining bring-up problem: the `rx_common` register
interface is accessible but does not control the DMA refill hang introduced by
the runtime bitstream switch.

## Report checklist

- [ ] Record pre-reload capture sample count.
- [ ] Record post-reload capture result (errno / success).
- [ ] Record `rx_common_ctrl` value written.
- [ ] Record post-reinit capture result.
- [ ] Attach `dmesg` diff between post-reload and post-reinit stages.

## Engineering conclusion template

```text
After hot-loading the runtime overlay, the host libiio capture path returned
errno ____ (____). Writing rx_common_ctrl = 0x____ over SSH did / did not
restore the capture path. Post-reinit libiio result: ____. The DMA starvation
is / is not recoverable with a single rx_common re-init because ______.
```
