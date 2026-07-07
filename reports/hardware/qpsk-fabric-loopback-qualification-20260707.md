# QPSK PL fabric-loopback qualification — 2026-07-07

## Result

The dual-modem QPSK core ran on the Zynq PL at BER=0 through the direct fabric loopback (`gp_ctrl[6]=1`). At `start_offset=62`, five independent stock-boot sessions succeeded and all 14 recorded attempts recovered 140/140 QPSK symbols, or 280 compared bits, with zero errors.

| Gate | Result |
|---|---:|
| Successful boot sessions | 5 / 5 |
| BER=0 attempts at offset 62 | 14 / 14 |
| Safe reboot to stock | 5 / 5 |
| Symbols / bits per attempt | 140 / 280 |
| Bitstream payload MD5 | `d8372303f18308586ae92d3d7f78e7b0` |
| Bitstream payload SHA256 | `945f05f82036298880b949f6347f8480b1615eb55ab4d7c8339d19af42a52050` |

The machine-readable aggregate is `docs/assets/lab1127_qpsk_fabric_qualification_20260707.json`.

## Scope

This is measured silicon evidence for the QPSK RTL, gpreg control path, mode mux, pulse shaping, receive chain and BER counter. The fabric loop bypasses AD9361 and RF; it does not establish OTA BER, EVM or carrier-recovery performance.

AD9361 digital-loopback diagnostics on the same payload reached `done + timeout` but received zero symbols with the raw RX source. That path remains a separate clock/FIFO/source-selection investigation.

## Vivado correlation

Two build flows must remain distinct:

| Flow | Board observation | Timing |
|---|---|---|
| Vendor snapshot `bridge_txrx_mux` | QPSK fabric BER=0, 5/5 boots | WNS -1.676 ns, TNS -53.405 ns, 66 failing endpoints |
| Standalone recreated project | gpreg responds, but TX/RX valid counters remain zero after runtime reload | WNS +0.354 ns, TNS 0 |

Therefore neither flow is ready for final signoff: the hardware-correlated snapshot must close timing, while the timing-clean standalone flow must restore runtime sample-clock activity.

## Reproduction

```powershell
python blocks/block_11_integrated_sdr_project/python/lab_11_27_runtime_qpsk_digital_loopback.py `
  --bit-bin-path tmp/bridge_txrx_mux.qpsk.wordswap.bit.bin `
  --loopback fabric `
  --start-offsets 62 `
  --retries 10 `
  --no-stop-on-zero `
  --tx-attenuation-db -89.75
```

Aggregate multiple run files with:

```powershell
python tools/aggregate_lab11_27_runs.py `
  "docs/assets/lab1127_runtime_qpsk_digital_loopback_live_20260707_qpsk_fabric*.json" `
  --start-offset 62 `
  --json-out docs/assets/lab1127_qpsk_fabric_qualification_20260707.json
```
