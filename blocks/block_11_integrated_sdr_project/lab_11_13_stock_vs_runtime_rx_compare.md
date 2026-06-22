# Lab 11.13 - Stock shell versus runtime overlay RX-path comparison

## Objective

Demonstrate, on the same live board and in one reproducible run, whether the
RX capture path already fails on the stock Linux shell or only after the course
overlay is hot-loaded through Linux `fpga_manager`.

This removes the remaining ambiguity from the earlier bring-up logs:

1. if stock-shell `libiio` and `iio_readdev` both fail, the problem is broader
   than the course overlay;
2. if stock-shell capture works but post-reload capture fails while `axi_gpreg`
   still answers, the blocker is specifically the runtime RX/DMAC path under
   the overlay.

## Files

| Path | Purpose |
|---|---|
| `blocks/block_11_integrated_sdr_project/python/lab_11_13_stock_vs_runtime_rx_compare.py` | runs the stock-shell baseline, hot-loads the corrected overlay, repeats the same RX checks, and optionally reboots back to the stock shell |
| `docs/assets/lab113_stock_vs_runtime_rx_compare_live.json` | consolidated live hardware report for the comparison run |

## What the script checks

For both the stock-shell stage and the post-reload stage, the helper records:

- compact AD9361 board state over SSH;
- IIO context summary from the host;
- one `axi_ad9361_adc_dma` register snapshot before and after capture attempts;
- one direct `libiio` host capture through `Buffer.refill()`;
- one `iio_readdev` capture through the same network IIO endpoint;
- a short `dmesg` tail.

For the runtime stage it also records:

- the uploaded `.bit.bin` payload checksum;
- Linux `fpga_manager` state and reload log tail;
- `axi_gpreg` ID/signature readback;
- one burst-control run with `tx_valid_count`, `rx_valid_count`, and
  `received_bits`.

## Run

```bash
python blocks/block_11_integrated_sdr_project/python/lab_11_13_stock_vs_runtime_rx_compare.py \
  --json-out docs/assets/lab113_stock_vs_runtime_rx_compare_live.json
```

The default flow reboots the board back to the stock shell after the runtime
checks so the lab bench is not left in the broken hot-reload state.

## Live result on 2026-06-23

The comparison now establishes the following sequence:

- before any overlay reload, the stock shell supports both a direct host-side
  `libiio` RX capture and a short `iio_readdev` capture; in the live report the
  stock `libiio` path returned `16384` complex samples and `iio_readdev`
  returned `65536` bytes with no stderr text;
- after the corrected `bridge_txrx_mux.wordswap.bit.bin` payload is hot-loaded
  through Linux `fpga_manager`, `axi_gpreg` becomes readable again and reports
  the known `tx_valid_count > 0`, `rx_valid_count = 0`, `received_bits = 0`
  pattern;
- after that same hot reload, both host-side capture paths fail on the RX side:
  direct `libiio Buffer.refill()` now fails with `OSError: [Errno 110] host unreachable`,
  and `iio_readdev` again reports refill timeout `Unknown error (110)`;
- the same comparison also shows that `cf-ad9361-dds-core-lpc` changes its
  visible `sync_start_enable` state from `arm` on the stock shell to `disarm`
  after the runtime hot load.

Practical consequence: the next bring-up step should focus on why the runtime
overlay leaves the AD9361 RX DMA / refill path starved even though the stock
shell baseline is healthy and the course gpreg block is visible.
