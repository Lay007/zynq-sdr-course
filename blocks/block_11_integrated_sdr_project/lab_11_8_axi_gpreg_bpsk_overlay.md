# Lab 11.8 - AD9361 gpreg BPSK overlay and first discovery burst

## Goal

Move from the placeholder AXI-Lite bring-up path to the first course-specific AD9361 hardware overlay that preserves a PS-visible control plane while the exact board-matched boot shell is re-established:

```text
PS / software -> axi_gpreg @ 0x79040000 -> staged sample-domain bridge -> AD9361 TX/RX path
```

This lab is the first clean handoff from the executable Block 5 modem toward the imported vendor AD9361 shell that matches the real course board (`xc7z020clg400-2`).

## Engineering decision

As of `2026-06-21`, the checked-in overlay mode is intentionally reduced to `gpreg_only`.

That rollback is deliberate:

- it keeps the control path simple and inspectable;
- it preserves the Linux-visible RX and TX DMA shell so the stock device tree still probes cleanly;
- it separates `axi_gpreg` address-map validation from the harder AD9361 clean-boot problem;
- it avoids treating a rebuilt but not yet boot-safe PL image as a valid RF measurement baseline.

The earlier burst-enabled TX experiments remain useful as historical evidence, but they are not the current safe checked-in baseline. The next gated step is to treat the extracted stock BOOT-partition payload as the only externally loaded boot-safe anchor for now, then explain why the source-correlated editable shells still lose AD9361 before more RF discovery work.

## New hardware files

| File | Purpose |
|---|---|
| `hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/system_project.tcl` | creates the clean course Vivado project for `xc7z020clg400-2` |
| `hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/system_bd.tcl` | sources the imported AD9361 baseline and adds the course overlay |
| `hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/vendor_system_bd_clg400.tcl` | frozen vendor block-design shell extracted from the working board image |
| `hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/build_bitstream.tcl` | deterministic batch build that emits the course bitstream and XSA |
| `hardware/7020_ad936x_sdr/rebuild_vendor_xpr_snapshot_mio_patch.tcl` | disposable Vivado flow that rebuilds the saved vendor `zc702.xpr` snapshot after patching only `sys_ps7` MIO14/15 |
| `hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/bpsk_zynq_ber_gpreg_bridge.v` | staged clock-domain bridge for the next sample-path reintegration step |
| `hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/course_dac_fifo_source_mux.v` | staged TX-path mux kept for the later DAC reintegration step, not enabled in the current `gpreg_only` mode |
| `hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/README.md` | build notes, register contract, and first-burst constraints |

## New software helper

| File | Purpose |
|---|---|
| `blocks/block_11_integrated_sdr_project/python/lab_11_8_axi_gpreg_bpsk_bringup.py` | programs the gpreg control words, launches one burst, polls `busy/done/timeout`, and reads BER counters |
| `blocks/block_11_integrated_sdr_project/python/lab_11_12_runtime_fpga_manager_reload.py` | uploads a checked `.bit.bin` payload over SSH, hot-loads it through Linux `fpga_manager`, then re-probes `axi_gpreg` and the host-visible IIO context |
| `blocks/block_11_integrated_sdr_project/python/lab_11_13_stock_vs_runtime_rx_compare.py` | proves on one live board run that stock-shell RX capture still works before reload, then repeats the same checks after runtime hot-load and records the breakage |
| `blocks/block_11_integrated_sdr_project/python/lab_11_15_runtime_bridge_rx_host_tx_probe.py` | hot-loads the intermediate `bridge_rx_only` overlay, runs one idle gpreg witness, then repeats the same witness while stock host TX transmits the shared BPSK burst, now also decoding the optional raw RX-tap `CAPTURE_DEBUG` word |
| `blocks/block_11_integrated_sdr_project/python/runtime_rx_common.py` | shared helper that reads and restores the stock RX common control request after the runtime overlay reload |
| `blocks/block_11_integrated_sdr_project/python/lab_11_16_runtime_rx_common_reinit_probe.py` | proves what the manual RX common re-init changes and what it still does not fix on the host capture path |
| `blocks/block_11_integrated_sdr_project/python/lab_11_17_runtime_rx_common_reinit_start_offset_sweep.py` | sweeps `start_offset` after the runtime RX common re-init while stock host TX drives the shared BPSK burst |

## Register contract

Base address: `0x79040000`

| Offset | Meaning |
|---|---|
| `0x000` | `axi_gpreg` version register |
| `0x004` | `axi_gpreg` ID register, expected `0x4250534B` |
| `0x404` | GPREG0 output: control word, bit `0` = start edge, bit `1` = clear sticky done, bits `3:2` = RX decision mode (`I`, `-I`, `Q`, `-Q`) |
| `0x408` | GPREG0 input: status word, bit `0` = synchronized start level, bit `1` = busy, bit `2` = sticky done, bit `3` = sticky RX timeout/abort |
| `0x444` | GPREG1 output: `FRAME_BIT_COUNT` |
| `0x448` | GPREG1 input: `RECEIVED_BITS` |
| `0x484` | GPREG2 output: `PREAMBLE_COUNT` |
| `0x488` | GPREG2 input: `TOTAL_ERRORS` |
| `0x4C4` | GPREG3 output: `START_OFFSET` |
| `0x4C8` | GPREG3 input: `PAYLOAD_ERRORS` |
| `0x508` | GPREG4 input: bridge signature, expected `0x4250534B` |
| `0x548` | GPREG5 input: packed `TX_VALID_COUNT` plus RX decision-sign debug |
| `0x588` | GPREG6 input: bridge-side `RX_VALID_COUNT` |
| `0x5C8` | GPREG7 input: packed raw RX-tap `CAPTURE_DEBUG` word |

`GPREG5` now packs one extra runtime witness alongside the low 12 bits of
`TX_VALID_COUNT`:

- bits `11:0`: `tx_valid_count_lsb12`;
- bits `19:12`: low 8 bits of the recovered-bit `1` count;
- bits `27:20`: low 8 bits of the recovered-bit valid count;
- bit `28`: any non-zero hard-decision input sample seen;
- bit `29`: any negative hard-decision input sample seen;
- bit `30`: any recovered bit `1` seen;
- bit `31`: any recovered-bit valid pulse seen.

`CAPTURE_DEBUG` packs one compact runtime witness word:

- bit `31`: any raw `capture_in_valid` pulse seen;
- bit `30`: any non-zero raw `RX1 I/Q` sample seen;
- bit `29`: any raw `capture_in_valid` pulse seen while the BER core was active;
- bit `28`: any raw `RX1 I` sample seen negative at the bridge tap;
- bit `27`: any raw `RX1 Q` sample seen negative at the bridge tap;
- bits `26:14`: low 13 bits of the raw `capture_in_valid` pulse count;
- bits `13:0`: peak absolute raw `RX1` sample magnitude in unsigned Q14 units.

## Build prerequisites

Generate the Block 5 memory files first:

```bash
python blocks/block_05_fpga_hdl_flow/python/generate_bpsk_rrc_tx_fir_vectors.py
python blocks/block_05_fpga_hdl_flow/python/generate_bpsk_framed_loopback_vectors.py
```

Then create the Vivado project and export the handoff:

```bash
vivado -mode batch -source hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/system_project.tcl
vivado -mode batch -source hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/build_bitstream.tcl
```

Expected outputs after a successful build:

1. bitstream at `hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/build/course_bpsk_fmcomms2_zc702.runs/impl_1/system_top.bit`;
2. XSA at `hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/course_bpsk_fmcomms2_zc702.sdk/system_top.xsa`;
3. timing logs at `hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/timing_synth.log` and `timing_impl.log`;
4. confirm that the new XSA contains `axi_gpreg_bpsk` at `0x79040000`;
5. reuse the helper below on Linux or over SSH.

## Local mock run

```bash
python blocks/block_11_integrated_sdr_project/python/lab_11_8_axi_gpreg_bpsk_bringup.py \
  --backend mock \
  --json-out docs/assets/lab118_axi_gpreg_bringup_mock.json
```

Expected local behavior:

- both the `axi_gpreg` ID and the bridge signature read back as `0x4250534B`;
- `busy_observed` and `done_observed` are both `true`;
- `timed_out_observed` is `false`;
- `received_bits == frame_bit_count`;
- `total_errors == 0`;
- `payload_errors == 0`.

## Linux or SSH run

Direct Linux `/dev/mem` access on the board:

```bash
sudo python blocks/block_11_integrated_sdr_project/python/lab_11_8_axi_gpreg_bpsk_bringup.py \
  --backend mmap \
  --base-addr 0x79040000 \
  --frame-bit-count 281 \
  --preamble-count 25 \
  --start-offset 62 \
  --json-out reports/lab118_axi_gpreg_bringup.json
```

Host-side remote `devmem` access over Ethernet:

```bash
python blocks/block_11_integrated_sdr_project/python/lab_11_8_axi_gpreg_bpsk_bringup.py \
  --backend ssh-devmem \
  --ssh-host 192.168.40.1 \
  --ssh-user root \
  --ssh-password analog \
  --base-addr 0x79040000
```

## Current live evidence

There are two evidence layers and they should not be conflated.

Historical burst-enabled overlay evidence:

The earlier hardware overlay was rebuilt, loaded through Linux `fpga_manager`, and probed from the host over Ethernet.

Historical evidence paths:

- XSA: `hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/course_bpsk_fmcomms2_zc702.sdk/system_top.xsa`;
- bitstream: `hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/build/course_bpsk_fmcomms2_zc702.runs/impl_1/system_top.bit`;
- live helper report: `docs/assets/lab118_axi_gpreg_bringup_live.json`.

Observed historical facts on the board:

- `devmem 0x79040000 32 -> 0x00040063`;
- `devmem 0x79040004 32 -> 0x4250534B`;
- `devmem 0x79040508 32 -> 0x4250534B`;
- helper result: `final_status = 0x0000080C`;
- `done_observed = true`;
- `timed_out_observed = true`;
- `received_bits = 0`;
- RF setup during the discovery run: TX attenuation `-60 dB`, RX gain manual `20 dB`, AGC disabled.

Runtime revalidation on `2026-06-23`:

The corrected word-swapped `bridge_txrx_mux` payload was reloaded again through
Linux `fpga_manager` from the stock-shell baseline, this time using the new
runtime helper:

- helper: `blocks/block_11_integrated_sdr_project/python/lab_11_12_runtime_fpga_manager_reload.py`;
- runtime reload report: `docs/assets/lab118_runtime_fpga_manager_reload_live.json`;
- post-reload gpreg report: `docs/assets/lab118_axi_gpreg_bringup_runtime_20260623.json`;
- post-reload burst-capture report: `docs/assets/lab110_iio_burst_capture_runtime_20260623.json`;
- post-reload compact RF sweep: `docs/assets/lab119_rf_discovery_sweep_runtime_20260623.json`.

Observed runtime facts on the board:

- baseline stock shell still returned a `Bus error` when reading `0x79040004`, so `axi_gpreg` was absent before the hot load;
- `fpga_manager` accepted `bridge_txrx_mux.wordswap.bit.bin` and remained in `operating` state;
- after the reload, `devmem 0x79040004 32 -> 0x4250534B` and `devmem 0x79040508 32 -> 0x4250534B` again;
- the gpreg burst helper still returned `final_status = 0x0000080C`, `tx_valid_count = 2376`, `rx_valid_count = 0`, and `received_bits = 0`;
- unlike the earlier broken live state, the host-side IIO context still enumerated `ad9361-phy`, `cf-ad9361-dds-core-lpc`, and `cf-ad9361-lpc` after the runtime reload;
- however, a short timed `iio_readdev` capture still returned refill timeout `Unknown error (110)` and produced zero samples;
- the compact safe-power RF sweep over `START_OFFSET = 48, 62, 74`, `RX gain = 10/20 dB`, and `TX attenuation = -80/-70 dB` kept the same result on every attempt: `received_bits = 0`, `tx_valid_count = 2376`, `rx_valid_count = 0`.

Stock-versus-runtime comparison on `2026-06-23`:

The dedicated comparison helper then ran one more stricter A/B check on the
same board:

- helper: `blocks/block_11_integrated_sdr_project/python/lab_11_13_stock_vs_runtime_rx_compare.py`;
- live comparison report: `docs/assets/lab113_stock_vs_runtime_rx_compare_live.json`.

Observed comparison facts on the board:

- before any hot load, the stock shell still supported both a direct host-side `libiio Buffer.refill()` capture and a short `iio_readdev` capture;
- in the live comparison, stock `libiio` returned `16384` complex samples and stock `iio_readdev` returned `65536` bytes with empty stderr;
- after the corrected runtime hot load, `axi_gpreg` remained readable and again reported `final_status = 0x0000080C`, `tx_valid_count = 2376`, `rx_valid_count = 0`, and `received_bits = 0`;
- after that same reload, direct host `libiio` failed with `OSError: [Errno 110] host unreachable`, while `iio_readdev` again failed with refill timeout `Unknown error (110)`;
- the same A/B report also showed `cf-ad9361-dds-core-lpc` changing from `sync_start_enable = arm` on the stock shell to `sync_start_enable = disarm` after the runtime reload.

Intermediate `bridge_rx_only` runtime witness on `2026-06-23`:

The next live runtime step moved from `bridge_txrx_mux` to the narrower
intermediate `bridge_rx_only` overlay so the vendor TX path stayed untouched
while the bridge reattached only to the RX sample tap.

- helper: `blocks/block_11_integrated_sdr_project/python/lab_11_15_runtime_bridge_rx_host_tx_probe.py`;
- earlier live witness report: `docs/assets/lab115_runtime_bridge_rx_host_tx_probe_live_20260623_bridge_rx_only_b.json`;
- refined live witness report: `docs/assets/lab115_runtime_bridge_rx_host_tx_probe_live_20260623_bridge_rx_only_debug_a.json`.

Observed `bridge_rx_only` facts on the board:

- the rebuilt `bridge_rx_only` raw `system_top.bit` was converted to the correct word-swapped runtime payload and accepted by Linux `fpga_manager`;
- after the hot load, the board still exposed `ad9361-phy`, `cf-ad9361-dds-core-lpc`, and `cf-ad9361-lpc`, with `axi_gpreg` again readable at `0x79040000`;
- the first idle gpreg witness still returned `tx_valid_count = 2376`, `rx_valid_count = 0`, and `received_bits = 0`;
- the helper then reconfigured stock AD9361 TX/RX for the shared deterministic BPSK burst at `915 MHz`, `3.84 MS/s`, `480 ksym/s`, `TX -50 dB`, `RX +35 dB`;
- even with that live host-driven stock TX burst active, the second witness still returned `tx_valid_count = 2376`, `rx_valid_count = 0`, and `received_bits = 0`;
- the refined `CAPTURE_DEBUG` witness then made the RX starvation more specific: both the idle probe and the host-TX probe read back `capture_debug_word = 0`, with `capture_valid_seen_any = false`, `capture_nonzero_seen_any = false`, `capture_valid_count_lsb15 = 0`, and `capture_peak_abs_max_q14 = 0`;
- the refined report conclusion is therefore stronger than the original `...bridge_rx_only_b.json` witness: after the runtime hot load, the bridge does not merely miss BER frames, it sees no raw RX-tap activity at all;
- the helper rebooted the board afterwards and confirmed a safe return to the stock shell baseline.

Runtime RX common re-init breakthrough on `2026-06-23`:

The next live step checked whether the runtime hot load left the AD9361 RX common
block in a different control state than the stock shell and whether forcing the
stock request bits back in would revive the live receive path.

- helper: `blocks/block_11_integrated_sdr_project/python/lab_11_16_runtime_rx_common_reinit_probe.py`;
- helper: `blocks/block_11_integrated_sdr_project/python/lab_11_17_runtime_rx_common_reinit_start_offset_sweep.py`;
- helper: `blocks/block_11_integrated_sdr_project/python/lab_11_18_runtime_rx_common_reinit_fresh_session_sweep.py`;
- live re-init probe: `docs/assets/lab116_runtime_rx_common_reinit_probe_live_20260623.json`;
- live host-TX witness after re-init: `docs/assets/lab116_runtime_rx_common_reinit_host_tx_probe_live_20260623.json`;
- live start-offset sweep after re-init: `docs/assets/lab117_runtime_rx_common_reinit_start_offset_sweep_live_20260623.json`.
- live fresh-session single-point decision-debug proof: `docs/assets/lab119_runtime_rx_decision_debug_single_point_live_20260623.json`;
- partial wide fresh-session start-offset sweep: `docs/assets/lab118_runtime_rx_common_reinit_fresh_session_start_offset_wide_live_20260623.json`.

Observed post-reinit facts on the board:

- right after the runtime hot load, the RX common request register fell back to `rx_common_ctrl_req = 0x00000000`, and the corresponding `rx_common_clk_count` / `rx_common_status` readbacks were both zero;
- restoring the stock request word `0x79020040 <- 0x00000003` revived non-zero RX clock/status activity immediately, with `rx_common_clk_count = 0x00013AE5` and `rx_common_status = 0x00000005`;
- the same re-init also cleared the raw input-side reset witness: `adc_input_reset_asserted_current` dropped to `false`, and both the input-side and RX-tap debug words became non-zero again;
- despite that fabric-side recovery, the dedicated A/B helper still reproduced the same host-side failures after the hot load: direct `libiio Buffer.refill()` still raised `OSError: [Errno 110] host unreachable`, and `iio_readdev` still failed with `Unable to refill buffer: Unknown error (110)`;
- the reinit-assisted host-TX witness then proved that the runtime overlay was no longer starved at the sample tap: `rx_valid_count` became non-zero, the raw `CAPTURE_DEBUG` word showed valid/non-zero activity, and the bridge could again observe the RX stream during stock host TX;
- the first checked-in `start_offset` sweep after that re-init found a real full-frame receive window on the first post-TX attempt: `start_offset = 32` completed `281` received bits with `144` total errors and `136` payload errors, while later attempts in the same TX session fell back to timeout-like behavior.
- a wider fresh-session sweep then removed simple `start_offset` blame from the shortlist: offsets from `0` through `576` kept the same `281 / 144 / 136` result, with identical `rx_valid_count = 2982` and `capture_peak_abs_max_q14 = 4095`;
- the new packed decision-sign witness finally made the failure mode explicit on a full-frame receive: the recovered-bit path asserted valid pulses, the hard-decision input was non-zero, but it never went negative and never produced a recovered `1`, so the live BER counters were effectively comparing the expected frame against an all-zero recovered bit stream.

Offset-binary root cause and post-fix live retune on `2026-06-23`:

- the stricter raw-sign witness `docs/assets/lab120_runtime_capture_sign_single_point_live_20260623.json` then showed that the raw bridge tap itself never went negative even though `capture_peak_abs_max_q14 = 4095`, which ruled out a dead RX path and pointed to a sample-format mismatch instead;
- inspecting the imported ADI HDL (`ad_datafmt.v` and `up_adc_channel.v`) explained why: with the default RX data-format controls left at zero, the `axi_ad9361` receive path exposes raw 12-bit offset-binary samples rather than signed two's-complement samples at the bridge tap;
- the bridge now corrects those low 12 bits locally before feeding `bpsk_zynq_ber_top`, while `CAPTURE_DEBUG` intentionally still reports the raw unformatted tap so the source-level explanation remains auditable;
- the immediate live post-fix proof `docs/assets/lab121_runtime_offset_binary_fix_single_point_live_20260623.json` showed that the old all-zero-stream failure is really gone: `decision_negative_seen_any = true` and `recovered_one_seen_any = true` now appear on hardware;
- the remaining BER is still high, but now tunable rather than collapsed: `docs/assets/lab122_runtime_offset_binary_fix_phase_sweep_live_20260623.json` improved the best point to `281 / 129 / 120` at `start_offset = 34`, `docs/assets/lab123_runtime_offset_binary_fix_tx_phase_sweep_live_20260623.json` showed only a modest extra gain from TX phase, and `docs/assets/lab124_runtime_offset_binary_fix_gain_sweep_live_20260623.json` reached the current best live runtime point `281 / 127 / 114` at `start_offset = 34`, `tx_phase = 315 deg`, `rx_gain = 5 dB`.

Self-timed `bridge_txrx_mux` follow-up on `2026-06-23`:

- the new runtime helper `blocks/block_11_integrated_sdr_project/python/lab_11_19_runtime_bridge_txrx_self_timed_bringup.py` removes the asynchronous host-side cyclic TX dependency and instead hot-loads `bridge_txrx_mux`, restores `rx_common`, configures AD9361, and launches the burst from the PL side through the same `start` control word;
- the first self-timed single-point proof `docs/assets/lab125_runtime_bridge_txrx_self_timed_single_point_live_20260623.json` showed that this path now completes a full `281`-bit frame with no timeout, which closes the earlier "missing-frame because TX is asynchronous" concern well enough to continue debugging BER on the deterministic path itself;
- the residual BER is still not low, so the next lightweight experiment added control-plane-selectable RX decision modes through GPREG0 bits `3:2`;
- the exploratory mode sweep `docs/assets/lab126_runtime_bridge_txrx_self_timed_mode_sweep_live_20260623.json` suggests that `neg-i` is better than the default `i` on the self-timed path, while the follow-up clean rerun `docs/assets/lab126_runtime_bridge_txrx_self_timed_neg_i_single_point_live_20260623.json` shows that the path still reaches a full frame but remains session-sensitive.

Current checked-in safety baseline:

- the stock-safe recovery path is still `hardware/7020_ad936x_sdr/stock_system_top_from_BOOT.bin`; under the old `uEnv.txt` `loadb`-on-`.bit.bin` fallback it was not proof of arbitrary external PL replacement, but under the new manual UART `fpga load` path it is now the only externally loaded boot-safe candidate demonstrated so far;
- the extracted stock BOOT partition is also the only externally loaded PL payload that now passes manual UART `fpga load` with AD9361 still alive; see `docs/assets/lab112_clean_boot_pl_validation.json`;
- the standalone vendor reference `hardware/7020_ad936x_sdr/ps/ad936x_no_os_reference/platform/hw/system_top.bit` remains the source-correlated raw control candidate, but it still fails AD9361 both as raw `fpga loadb` and as manual `.bit.bin` `fpga load`;
- `hardware/7020_ad936x_sdr/boot/validate_clean_boot_overlay.py` captures the decisive UART evidence for raw `fpga loadb`, while `hardware/7020_ad936x_sdr/boot/validate_manual_uart_fpga_load.py` now covers the manual `.bit.bin` `fpga load` path;
- the rebuilt `vendor_only` shell now also passes Vivado project creation, implementation, bitstream generation, and XSA export, but still fails clean boot with the same AD9361 calibration timeout;
- the new `bridge_rx_only` mode now passes Vivado project creation, implementation, bitstream generation, and XSA export;
- the saved vendor `zc702.xpr` snapshot, rebuilt through `hardware/7020_ad936x_sdr/rebuild_vendor_xpr_snapshot_mio_patch.tcl`, still exports an XSA with zero module/memrange/parameter drift against the vendor reference, but its direct raw `system.bit` load still fails AD9361 clean boot with the same calibration timeout;
- the newer `bridge_txrx_mux` raw-clean-boot candidate now proves that the course-owned overlay really reaches PL and exposes `axi_gpreg` on the board after reboot; see `docs/assets/lab118_axi_gpreg_bringup_cleanboot_raw.json`;
- the earlier helper-generated `bridge_txrx_mux.bit.bin` candidate was rejected by U-Boot `fpga load` with `zynq_validate_bitstream: Bitstream is not validated yet (diff 1700)`, so the later healthy AD9361 state in that path came from the untouched stock PL shell;
- after fixing the `.bit -> .bit.bin` conversion to the correct word-swapped payload, the regenerated `bridge_txrx_mux.bit.bin` candidate is now accepted by manual UART `fpga load`, but Linux still falls into the same AD9361 calibration timeout and exposes only `iio:device0`;
- regenerated boot-time candidates from both `AD936X_PL.zip` and `AD936X_only_PL.zip` were rejected and summarized in `docs/assets/lab112_clean_boot_pl_validation.json`.

Interpretation:

- the PS-to-PL gpreg control plane was validated on real hardware at least once in the earlier burst-enabled overlay;
- the same gpreg control plane is now also readable after a direct raw clean boot of the `bridge_txrx_mux` candidate, with both ID and signature equal to `0x4250534B`, `tx_valid_count > 0`, and `rx_valid_count == 0`;
- the corrected runtime `fpga_manager` reload now reproduces the same gpreg readback from the stock Linux shell without losing basic IIO device enumeration, so the blocker is no longer "the board cannot see the overlay at all";
- the stock-versus-runtime comparison now proves that the stock Linux shell still supports both host RX capture paths before any reload, while the runtime hot load breaks both of them even though `axi_gpreg` stays visible;
- the refined `bridge_rx_only` runtime witness now adds a stronger negative result: even when the stock vendor TX path transmits the shared BPSK burst successfully, the bridge still sees `rx_valid_count = 0` and the raw RX-tap `CAPTURE_DEBUG` word remains all zeros;
- the runtime RX common re-init result is stronger than the earlier negative witness: the fabric-side RX path can now be revived after the hot load, but the host libiio/DMAC capture path still remains broken;
- the first post-reinit `start_offset` sweep shows that the runtime BPSK receive path is now alive enough to complete a full `281`-bit receive attempt, so the blocker is no longer dead RX plumbing;
- the offset-binary explanation closes that specific bug: the receive chain is no longer stuck with unsigned raw AD9361 samples, and negative decisions / recovered `1` bits now appear on hardware;
- the new self-timed `bridge_txrx_mux` result removes the earlier "host-side cyclic TX is the whole problem" explanation: full frames are now reproducible without timeout on the PL-owned TX/RX path, but BER still depends on decision polarity and drifts across sessions;
- the next blocker is therefore a narrower receive-side problem: stabilize the deterministic self-timed path, then decide whether the right next step is a slightly richer phase/axis correction stage or a true preamble/frame detector in the FPGA receive path;
- the normalized pure-Tcl `vendor_only` flow now eliminates the earlier `MIO14/15` drift, but it is still blocked by four read-only or disabled derived parameters: `sys_ps7.PCW_S_AXI_HP0_FREQMHZ`, `axi_ad9361_adc_dma.DMA_AXI_PROTOCOL_SRC`, `axi_ad9361_dac_dma.DMA_AXI_PROTOCOL_DEST`, and `axi_ad9361.SPEED_GRADE`; see `docs/assets/vendor_reference_vs_vendor_only_handoff_diff.json`;
- the saved vendor `zc702.xpr` snapshot is still the preferred editable source witness once rebuilt through the MIO14/15 patch flow, but it is not yet a boot-safe RF baseline; see `docs/assets/vendor_reference_vs_vendor_xpr_mio14_15_patch_handoff_diff.json`;
- the current checked-in HDL now also includes an intermediate `bridge_rx_only` reintegration mode that is validated in Vivado but not yet in clean boot;
- the extracted stock partition from `BOOT.bin` is now the only externally loaded boot-safe reintegration anchor, but it is not yet editable or source-correlated enough for the final course overlay;
- the immediate next task is to remove the remaining asynchronous-frame ambiguity from the runtime BER path, then continue retuning timing / phase with the sample-format bug already closed, while separately continuing the boot-safe-shell investigation for the editable clean-boot path.

## Next gated re-enable order

1. Confirm that the candidate custom boot-time PL image is accepted by the relevant validator path: raw `.bit` through `validate_clean_boot_overlay.py` or `.bit.bin` through `validate_manual_uart_fpga_load.py`.
2. Confirm the board IP, `axi_gpreg` ID register, and bridge signature before writing frame parameters.
3. Re-enable the sample-domain bridge while keeping the Linux-visible DMA shell intact.
4. Keep AD9361 TX attenuation at the minimum output power setting available on the board.
5. Keep RX gain low and manual. Do not enable AGC for the first renewed burst.
6. Launch one short burst only.
7. Observe `busy` and then `done` or `done after timeout`.
8. Read `RECEIVED_BITS`, `TOTAL_ERRORS`, and `PAYLOAD_ERRORS`.
9. Only then resume repeated sweeps or BER campaigns.

## Report checklist

- [ ] Attach the regenerated XSA path and confirm `axi_gpreg_bpsk`.
- [ ] Attach the regenerated bitstream path.
- [ ] Show the `0x79040000` base address in the exported handoff.
- [ ] Record one successful ID readback and one successful signature readback.
- [ ] Show programmed `FRAME_BIT_COUNT`, `PREAMBLE_COUNT`, and `START_OFFSET`.
- [ ] State whether `busy`, `done`, and `timeout` were observed.
- [ ] Record `RECEIVED_BITS`, `TOTAL_ERRORS`, and `PAYLOAD_ERRORS`.
- [ ] List the AD9361 TX attenuation and RX gain used for the first renewed burst.

## Engineering conclusion template

```text
The gpreg-based AD9361 overlay is ready / not ready as a clean-boot baseline.
The exported handoff contains / does not contain the expected control window.
The next gated reintegration step is ______ and its success criterion is ______.
```
