# Lab 11.27 — Runtime QPSK digital-loopback BER

## Objective

Validate the QPSK modem through the same runtime PL control plane and AD9361 digital-loopback route used by the promoted BPSK result. The experiment selects QPSK through `gp_ctrl[4]`, sweeps the sampling start offset and records every attempt instead of keeping only the best run.

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

## Board command

```bash
python blocks/block_11_integrated_sdr_project/python/lab_11_27_runtime_qpsk_digital_loopback.py \
  --start-offsets 96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111 \
  --retries 20 \
  --run-tag qpsk_clean_boot_01
```

The helper reloads the runtime payload, rebinds the required DDS/ADC drivers, configures the digital loopback, runs the sweep, writes JSON evidence and restores the stock state by reboot unless `--no-reboot-after` is specified.

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

## Current limitation

The repository contains the runtime helper and passing RTL proof, but no promoted Lab 11.27 board JSON yet. Therefore the QPSK runtime path is `executable / hardware-pending`, not measured.
