# Lab 11.14 - Stock-shell host BPSK OTA fallback

## Objective

Provide a practical RF fallback path while the integrated PL BPSK overlay is
still blocked on the runtime RX refill / `rx_valid_count` problem.

This lab does **not** use the course PL modem. Instead, it uses the clean stock
AD9361 Linux shell and host-side `libiio` buffers to:

- synthesize a deterministic BPSK burst from the same course preamble/payload
  idea used by the reference package;
- transmit that burst over the stock TX DMA path;
- capture it back on the stock RX DMA path;
- detect the frame, align symbols, and report BER/EVM.

That makes it useful for two things:

1. proving that the short over-the-air TX1 -> RX1 path itself is viable;
2. separating RF-link problems from the still-open PL overlay bring-up problem.

## Files

| Path | Purpose |
|---|---|
| `blocks/block_11_integrated_sdr_project/python/lab_11_14_stock_shell_bpsk_ota.py` | host-driven stock-shell BPSK TX/RX helper with BER/EVM analysis |

## Run

For the next live bench run on a clean stock boot:

```bash
python blocks/block_11_integrated_sdr_project/python/lab_11_14_stock_shell_bpsk_ota.py \
  --run-tag live_ota_bpsk
```

The helper will:

- configure the stock AD9361 TX/RX path;
- disable DDS tone generators;
- push a cyclic BPSK burst through `cf-ad9361-dds-core-lpc`;
- capture a short `CI16` RX window from `cf-ad9361-lpc`;
- save the capture, TX reference, manifest, JSON metrics, and basic plots.

## Safe first settings

The checked-in defaults are intentionally conservative:

- center frequency `915 MHz`;
- sample rate `3.84 MS/s`;
- symbol rate `240 ksym/s` with `16` samples/symbol;
- TX attenuation `-50 dB`;
- RX manual gain `35 dB`.

If the preamble does not lock, increase RX gain first before raising TX power.

## Synthetic self-test

Before touching hardware, the script can verify its own waveform-generation and
frame-detection logic locally:

```bash
python blocks/block_11_integrated_sdr_project/python/lab_11_14_stock_shell_bpsk_ota.py \
  --synthetic-test \
  --run-tag synthetic_selftest
```

This path is already self-checked and reaches zero BER locally.

## Current status

As of `2026-06-23`, this helper is prepared as the next clean-bench fallback
step. The need for it comes directly from the current bring-up split:

- the stock shell still supports host RX capture before any overlay reload;
- the runtime-loaded course overlay restores `axi_gpreg`, but still starves the
  RX refill path afterwards;
- therefore the next RF question is best answered on the stock shell first,
  using host-driven BPSK over the proven TX/RX DMA path.

The next live run should happen only after the board is back on a clean stock
boot, because the last runtime driver-rebind experiment left the current bench
state requiring a fresh recovery cycle.
