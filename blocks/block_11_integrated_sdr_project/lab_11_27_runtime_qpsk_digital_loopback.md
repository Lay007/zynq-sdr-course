# Lab 11.27 — Runtime QPSK digital-loopback BER

## Objective

Validate the QPSK modem through the runtime PL control plane. The helper supports a direct PL fabric loopback for deterministic modem qualification and a separate AD9361 digital-loopback diagnostic. It selects QPSK through `gp_ctrl[4]` and records every attempt.

## What is already proven without hardware

The canonical HDL suite checks:

- Gray-coded QPSK symbol mapping;
- 140-symbol / 280-bit QPSK modem loopback at BER=0;
- the dual-modem gpreg bridge at BER=0;
- ordered transfer of 500 samples through the asynchronous RX clock-domain FIFO.

Run the software proof with:

```bash
python tools/run_block5_hdl_smoke.py --no-generate
```

## Board commands

Deterministic PL fabric qualification, without AD9361 or RF transmission:

```bash
python blocks/block_11_integrated_sdr_project/python/lab_11_27_runtime_qpsk_digital_loopback.py \
  --bit-bin-path tmp/bridge_txrx_mux.qpsk.cdcfix_20260707.wordswap.bit.bin \
  --loopback fabric \
  --start-offsets 62 \
  --retries 10 \
  --no-stop-on-zero \
  --tx-attenuation-db -89.75
```

AD9361 BIST diagnostic:

```bash
python blocks/block_11_integrated_sdr_project/python/lab_11_27_runtime_qpsk_digital_loopback.py \
  --start-offsets 96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111 \
  --loopback ad9361 \
  --retries 20 \
  --run-tag qpsk_clean_boot_01
```

The helper reloads the runtime payload, runs the selected loopback, writes every attempt and debug counter to JSON, and restores the stock state by reboot unless `--no-reboot-after` is specified. AD9361 driver rebind/configuration is skipped in fabric mode.

## Acceptance gates

| Gate | Required result |
|---|---|
| Control plane | expected gpreg ID is read and the QPSK mode bit is active |
| Frame completeness | 140/140 QPSK symbols are received |
| Bit count | 280 compared bits per complete frame |
| Correctness | zero bit errors for a passing attempt |
| Repeatability | report success count / total attempts for every start offset |
| Recovery | stock IIO context is available after the experiment |

A single best BER=0 attempt is evidence that the datapath works, not that it is deterministic. Promotion to `measured` requires a clean-boot series with the full attempt table and a stated success rate.

## Required artifacts

- JSON output from the helper;
- bitstream/XSA identity and Git commit;
- AD9361 configuration snapshot;
- per-offset attempt and success counts;
- short conclusion separating functional success from repeatability;
- optional RTL-SDR spectrum witness when an antenna or cabled path is added later.

## Measured result — 2026-07-07

The CDC-fixed, timing-clean QPSK payload reached BER=0 at `start_offset=62`. Four independent stock→runtime→stock sessions passed, and all 13 attempts at the selected offset recovered 140 symbols / 280 bits with zero errors. Every session returned to stock successfully.

See `reports/hardware/qpsk-fabric-loopback-qualification-20260707.md` and `docs/assets/lab1127_qpsk_fabric_cdcfix_qualification_20260707.json`.

The result qualifies the QPSK core on silicon but bypasses AD9361 and RF. The AD9361 raw digital-loopback source still returns zero QPSK symbols. The hardware-working vendor-snapshot bitstream now meets timing with WNS `+0.003 ns`; external RTL-SDR QPSK evidence and stronger timing margin remain open gates.
