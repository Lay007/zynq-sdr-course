# Lab 11.11 - Contention probe between host IIO capture and gpreg burst control

## Goal

Determine whether the current course overlay can support host-side `iio_readdev` capture and PS-side `gpreg` burst control at the same time, or whether those two operations interfere with each other.

## Engineering question

> Is the current blocker a missing RF signal, or a deeper contention between the Linux IIO capture path and direct `devmem` access to the course gpreg block?

## Script

| File | Purpose |
|---|---|
| `blocks/block_11_integrated_sdr_project/python/lab_11_11_iio_gpreg_contention_probe.py` | runs standalone and overlapping capture scenarios, snapshots `axi_ad9361_adc_dma`, and records which side fails under overlap |

## Minimum scenario set

The probe should include three scenarios:

1. standalone `iio_readdev` capture;
2. short overlapping capture with a near-immediate burst trigger;
3. longer overlapping capture with a later burst trigger.

That is enough to separate:

- "IIO never works";
- "gpreg never works";
- "both work alone but interfere under overlap."

## Example run

```bash
python blocks/block_11_integrated_sdr_project/python/lab_11_11_iio_gpreg_contention_probe.py \
  --ssh-host 192.168.40.1 \
  --ssh-user root \
  --ssh-password analog \
  --iio-uri ip:192.168.40.1 \
  --json-out docs/assets/lab111_iio_gpreg_contention_probe_live.json
```

## Report contract

The JSON report should capture:

- AD9361 state before and after the probe;
- one `axi_ad9361_adc_dma` register snapshot before and after each scenario;
- standalone capture result;
- overlapping capture result;
- overlapping burst-helper result;
- the last `dmesg` lines after each scenario.

## Interpretation

If standalone capture succeeds but overlapping scenarios fail asymmetrically, the course should treat that as a structural integration problem, not as a BER-tuning problem.

Typical outcomes:

- capture succeeds, burst fails with `Bus error`;
- burst succeeds, capture fails with refill timeout;
- both succeed only when not overlapping.

Those outcomes point toward an integration or arbitration issue around the live PL design, not toward ordinary RX gain or `START_OFFSET` tuning.

## Current live note

Live follow-up on `2026-06-21` split the problem into two separate layers:

- disabling the `axi_gpreg_bpsk` clock-monitor input removed the earlier overlap-time `Bus error` on `0x79040004`;
- the same rebuilt overlay still disturbed the Linux RX capture stack when it was hot-loaded through `fpga_manager` on an already running system;
- after that hot reload, `gpreg` access recovered but standalone `iio_readdev` captures returned refill timeout `Unknown error (110)`;
- a manual U-Boot `fpga load` of the same bitstream before Linux boot proved that the older “remove DAC DMA from PL” overlay panics the kernel in `axi_dmac_probe()`, so the stock Linux device tree still expects that TX DMA path to exist in hardware;
- attempting to recover the RX DMA path with Linux platform-driver `unbind` / `bind` caused a kernel oops in `dma_channel_rebalance()`.

Second live follow-up on `2026-06-23` narrowed the failure mode further:

- the corrected word-swapped `bridge_txrx_mux` payload was hot-loaded again from the stock-shell baseline through `fpga_manager`;
- the host still saw the three-device IIO context (`ad9361-phy`, `cf-ad9361-dds-core-lpc`, `cf-ad9361-lpc`) after the reload;
- `axi_gpreg` also became readable again and the burst helper repeated the known `done + timeout`, `tx_valid_count = 2376`, `rx_valid_count = 0`, `received_bits = 0` result;
- however, a short timed `iio_readdev` capture still returned refill timeout `Unknown error (110)` with zero samples;
- a compact safe-power RF sweep over multiple `START_OFFSET`, RX-gain, and TX-attenuation combinations still produced no RX-side activity.

Third live follow-up on `2026-06-23` removed the last remaining stock-shell ambiguity:

- the dedicated comparison helper `blocks/block_11_integrated_sdr_project/python/lab_11_13_stock_vs_runtime_rx_compare.py` verified that a fresh stock shell still supports both a direct host `libiio Buffer.refill()` capture and a short `iio_readdev` capture before any overlay reload;
- the same helper then hot-loaded the corrected payload through `fpga_manager`, confirmed `axi_gpreg` readback again, and reproduced the same runtime failure on both host RX paths: `libiio` failed with `OSError: [Errno 110] host unreachable` and `iio_readdev` failed with refill timeout `Unknown error (110)`;
- the same comparison also showed `cf-ad9361-dds-core-lpc` changing from `sync_start_enable = arm` on the stock shell to `sync_start_enable = disarm` after the runtime reload.

Practical consequence: the blocker is now narrower than "runtime reload breaks everything". The stock shell baseline is healthy, the current runtime image keeps `fpga_manager`, `axi_gpreg`, and basic IIO enumeration alive, but the RX DMA / refill path still does not deliver usable samples and the bridge still sees no RX-valid traffic. Do not use live `fpga_manager` reload plus driver rebinding as the normal course workflow until the board has been revalidated after a clean boot.

## Engineering conclusion template

```text
Standalone IIO capture ______.
Short overlap caused ______.
Long overlap caused ______.
The next step is to inspect ______ before doing more BER sweeps.
```
