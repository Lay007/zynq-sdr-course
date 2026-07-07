# QPSK PL fabric-loopback qualification — 2026-07-07

## Result

The dual-modem QPSK core ran on the Zynq PL at BER=0 through the direct fabric loopback (`gp_ctrl[6]=1`). The final CDC-fixed, timing-clean payload completed four independent stock-boot sessions and all 13 recorded attempts at `start_offset=62` recovered 140/140 QPSK symbols, or 280 compared bits, with zero errors.

| Gate | Result |
|---|---:|
| Successful boot sessions | 4 / 4 |
| BER=0 attempts at offset 62 | 13 / 13 |
| Safe reboot to stock | 4 / 4 |
| Symbols / bits per attempt | 140 / 280 |
| Bitstream payload MD5 | `414eca88fe628de06c9bef09cf73e30e` |
| Bitstream payload SHA256 | `48a17b8cbabec9c7d9c5236cb665397d154813e6537c24067765f601d73ead28` |

The machine-readable aggregate is `docs/assets/lab1127_qpsk_fabric_cdcfix_qualification_20260707.json`. The earlier pre-fix qualification remains preserved separately as historical functional evidence, but is not the signoff payload.

## Scope

This is measured silicon evidence for the QPSK RTL, gpreg control path, mode mux, pulse shaping, receive chain and BER counter. The fabric loop bypasses AD9361 and RF; it does not establish OTA BER, EVM or carrier-recovery performance.

AD9361 digital-loopback diagnostics on the same payload reached `done + timeout` but received zero symbols with the raw RX source. That path remains a separate clock/FIFO/source-selection investigation.

## Vivado correlation

The RX channel-select control originally crossed from `sample_clk` into the raw ADC FIFO write path without a destination-domain synchronizer. The final payload adds a two-flop `ASYNC_REG` synchronizer in `adc_input_clk` and constrains only capture into its first stage.

| Flow | Board observation | Timing |
|---|---|---|
| Vendor snapshot `bridge_txrx_mux`, CDC-fixed | QPSK fabric BER=0, 4/4 boots and 13/13 attempts | WNS +0.003 ns, TNS 0, 0 failing endpoints |
| Standalone recreated project | gpreg responds, but TX/RX valid counters remain zero after runtime reload | WNS +0.354 ns, TNS 0 |

The CDC-fixed vendor snapshot is the first payload that both meets routed timing and passes the board qualification. The raw Vivado bitstream is 2,505,900 bytes with SHA256 `973bb897010af1f5e3c31ccbd37b69e8e5ecf8abe624edea8e5a42954feb4e41`. WNS is only `+0.003 ns`, so closure is valid for this implementation but repeat-build or seed stability is not yet demonstrated.

## Reproduction

```powershell
python blocks/block_11_integrated_sdr_project/python/lab_11_27_runtime_qpsk_digital_loopback.py `
  --bit-bin-path tmp/bridge_txrx_mux.qpsk.cdcfix_20260707.wordswap.bit.bin `
  --loopback fabric `
  --start-offsets 62 `
  --retries 10 `
  --no-stop-on-zero `
  --tx-attenuation-db -89.75
```

Aggregate multiple run files with:

```powershell
python tools/aggregate_lab11_27_runs.py `
  "docs/assets/lab1127_runtime_qpsk_digital_loopback_live_20260707_qpsk_fabric_cdcfix*.json" `
  --start-offset 62 `
  --json-out docs/assets/lab1127_qpsk_fabric_cdcfix_qualification_20260707.json
```
