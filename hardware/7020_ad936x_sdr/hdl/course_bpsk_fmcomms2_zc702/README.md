# Course BPSK FMCOMMS2 Overlay for the CLG400 Zynq SDR

This directory is the course-specific Vivado overlay for the imported AD9361/FMCOMMS2 reference captured from the working board image. It keeps the vendor HDL baseline intact and adds a staged BPSK reintegration path that can be enabled one slice at a time.

## What this overlay changes

- targets the real board part `xc7z020clg400-2`;
- reuses the imported vendor AD9361 block-design shell from `vendor_system_bd_clg400.tcl`;
- adds an `axi_gpreg` control/status plane at `0x79040000`;
- stages `bpsk_zynq_ber_gpreg_bridge.v`, which clocks the modem from `util_ad9361_divclk/clk_out`;
- keeps the optional `axi_gpreg` clock-monitor input disabled, because the live overlap probe on `2026-06-21` linked that path to AXI-Lite external-abort failures during concurrent host IIO capture;
- can route `RX1 I/Q` samples from `util_ad9361_adc_fifo` into the BPSK BER core in the intermediate `bridge_rx_only` mode;
- keeps the stock DAC DMA and `util_ad9361_dac_upack` transmit path untouched in both checked-in non-vendor modes, while the course modem still exposes its internal `tx_sample_bus` for the later TX reintegration step.

That last point is intentional: this overlay is currently used to re-establish clean AD9361 boot and IIO visibility before the deterministic burst waveform is reattached to the live TX path.

## Overlay modes

`system_bd.tcl` supports four explicit modes:

- `vendor_only`: leave the imported vendor shell untouched;
- `gpreg_only`: add only the PS-visible `axi_gpreg` window and a signature-safe control-plane baseline;
- `bridge_rx_only`: keep the vendor DAC/TX path untouched, but reconnect the sample-domain BPSK bridge and the `RX1` sample tap so timeout/status behavior can be revalidated before TX reintegration;
- `bridge_txrx_mux`: keep the vendor DMA/TX chain instantiated, but switch the DAC FIFO source over to the course BPSK TX path only while the bridge burst is active.

The safe default remains `gpreg_only`. To build the intermediate bridge mode in PowerShell:

```powershell
$env:COURSE_OVERLAY_MODE = "bridge_rx_only"
vivado -mode batch -source hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/system_project.tcl
Remove-Item Env:COURSE_OVERLAY_MODE
```

That intermediate mode is now Vivado-validated: on `2026-06-21`, it completed
`system_project.tcl`, `build_bitstream.tcl`, `write_bitstream`, and XSA export
successfully. It is not yet boot-validated on hardware, because the resulting
`system.bit.bin` still triggers `ad9361 spi0.0: Calibration TIMEOUT (0x244,
0x80)` during clean boot.

The same clean-boot failure now also holds for `vendor_only`. That matters:
the current blocker is no longer "the course bridge broke AD9361", but "the
reconstructed source shell still differs from the vendor handoff that booted on
the board image."

The most useful source-correlated raw-bit control candidate is still the
standalone vendor reference bitstream at
`../../ps/ad936x_no_os_reference/platform/hw/system_top.bit`, because it proves
that raw `fpga loadb` really reaches PL on this board. It is not a clean-boot
radio baseline, though: on `2026-06-22`, both the raw `fpga loadb` path and the
manual `.bit.bin` `fpga load` path still ended with
`ad9361 spi0.0: Calibration TIMEOUT (0x244, 0x80)`.

The only externally loaded boot-safe baseline demonstrated so far is the
extracted `../../boot/sd_image/BOOT.bin` partition payload at
`../../stock_system_top_from_BOOT.bin`, which survives manual UART `fpga load`
and returns Linux plus all `4` expected IIO devices.

`../../compare_xsa_handoffs.py` now captures that drift explicitly. After
forcing `CONFIG.preset {None}` in the recreated course flow on `2026-06-22`,
the pure-Tcl `vendor_only` rebuild still matched the vendor reference XSA in
module count and memrange count, and the `MIO14/15` drift disappeared, but
four common-IP parameters remained different:

- `sys_ps7`: `PCW_S_AXI_HP0_FREQMHZ`
- `axi_ad9361_adc_dma`: `DMA_AXI_PROTOCOL_SRC`
- `axi_ad9361_dac_dma`: `DMA_AXI_PROTOCOL_DEST`
- `axi_ad9361`: `SPEED_GRADE`

Those four fields are read-only or disabled in the recreated BD flow, so
reapplying them with `set_property` does not stick. The persistent pure-Tcl
report lives at
`../../../../docs/assets/vendor_reference_vs_vendor_only_handoff_diff.json`.

A separate rebuild from the saved vendor
`../../adi_fmcomms2_reference/projects/fmcomms2/zc702/zc702.xpr` snapshot is
now promoted to the preferred editable shell baseline when driven through
`../../rebuild_vendor_xpr_snapshot_mio_patch.tcl`. On `2026-06-22`, patching
only `PCW_MIO_14_DIRECTION` and `PCW_MIO_15_DIRECTION` before synth/impl/export
produced:

- an XSA with zero module/memrange/parameter drift against the vendor
  reference handoff;
- a raw `system_top.bit` with a different MD5 from the bundled no-OS reference
  bit;
- a raw direct-load result that still reproduces the same AD9361 calibration
  timeout as the source-correlated vendor reference payload.

The historical unpatched snapshot report still lives at
`../../../../docs/assets/vendor_reference_vs_vendor_xpr_snapshot_handoff_diff.json`.
The zero-drift patched report lives at
`../../../../docs/assets/vendor_reference_vs_vendor_xpr_mio14_15_patch_handoff_diff.json`.

## Control-plane contract

Base address: `0x79040000`

| Offset | Meaning |
|---|---|
| `0x000` | `axi_gpreg` version register |
| `0x004` | `axi_gpreg` ID, configured to `0x4250534B` |
| `0x404` | GPREG0 output: control word, bit `0` = start edge, bit `1` = clear sticky done, bits `3:2` = RX decision mode (`I`, `-I`, `Q`, `-Q`) |
| `0x408` | GPREG0 input: status word, bit `0` = synchronized start level, bit `1` = busy, bit `2` = sticky done, bit `3` = sticky RX timeout/abort |
| `0x444` | GPREG1 output: `FRAME_BIT_COUNT` |
| `0x448` | GPREG1 input: `RECEIVED_BITS` |
| `0x484` | GPREG2 output: `PREAMBLE_COUNT` |
| `0x488` | GPREG2 input: `TOTAL_ERRORS` |
| `0x4C4` | GPREG3 output: `START_OFFSET` |
| `0x4C8` | GPREG3 input: `PAYLOAD_ERRORS` |
| `0x508` | GPREG4 input: bridge signature word `0x4250534B` |
| `0x548` | GPREG5 input: packed `TX_VALID_COUNT` plus RX decision-sign debug |
| `0x588` | GPREG6 input: `RX_VALID_COUNT` observed by the bridge sample clock |
| `0x5C8` | GPREG7 input: packed `CAPTURE_DEBUG` word from the raw RX tap |

`GPREG5` now carries both the low 12 bits of `TX_VALID_COUNT` and a compact
decision-sign witness:

- bits `11:0`: `tx_valid_count_lsb12`;
- bits `19:12`: low 8 bits of the recovered-bit `1` count;
- bits `27:20`: low 8 bits of the recovered-bit valid count;
- bit `28`: at least one non-zero hard-decision input sample was seen;
- bit `29`: at least one negative hard-decision input sample was seen;
- bit `30`: at least one recovered bit `1` was seen;
- bit `31`: at least one recovered-bit valid pulse was seen.

`CAPTURE_DEBUG` is intentionally compact so it survives the same control-plane
path as the BER counters:

- bit `31`: at least one raw `capture_in_valid` pulse was seen;
- bit `30`: at least one non-zero raw `RX1 I/Q` sample was seen;
- bit `29`: a raw `capture_in_valid` pulse was seen while the BER core was
  active;
- bit `28`: at least one raw `RX1 I` sample was negative at the bridge tap;
- bit `27`: at least one raw `RX1 Q` sample was negative at the bridge tap;
- bits `26:14`: low 13 bits of the raw `capture_in_valid` pulse count;
- bits `13:0`: peak absolute `RX1` sample magnitude in unsigned Q14 units.

## Build prerequisites

The Block 5 ROM images are generated files and are intentionally not committed. Generate them from the repository root before running Vivado:

```bash
python blocks/block_05_fpga_hdl_flow/python/generate_bpsk_rrc_tx_fir_vectors.py
python blocks/block_05_fpga_hdl_flow/python/generate_bpsk_framed_loopback_vectors.py
```

## Vivado flow

Use Vivado `2021.1` from the repository root:

```bash
vivado -mode batch -source hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/system_project.tcl
vivado -mode batch -source hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/build_bitstream.tcl
```

The scripts create the project under `build/` and place the stable handoff artifacts here:

- bitstream: `build/course_bpsk_fmcomms2_zc702.runs/impl_1/system_top.bit`
- hardware handoff: `course_bpsk_fmcomms2_zc702.sdk/system_top.xsa`
- timing logs: `timing_synth.log` and `timing_impl.log`

The current clean build closes timing and exports `system_top.xsa` without the earlier `bad_timing` fallback.

## Runtime loading note

The current safe engineering assumption is:

- use this overlay as a boot-time PL image, not as a hot PL reload on top of a live Linux IIO stack;
- when booting it from the stock Pluto-like SD image, use `../../boot/course_clean/uEnv_course_bpsk_overlay.txt` as the FAT-root `uEnv.txt` so U-Boot removes the stale `/fpga-axi/i2c@41600000` and `/fpga-axi/mwipcore@43c00000` Linux nodes before `bootm`;
- keep the vendor TX FIFO path untouched in this bring-up phase; treat the checked-in non-vendor modes as control-plane / RX-observation overlays, not yet as the final burst-TX image;
- if you must reload it at runtime for debugging, re-validate both `iio_readdev` and `axi_gpreg` access afterwards before trusting any BER or RF result;
- the old "all-zero recovered stream" explanation is now closed: the raw bridge tap was offset-binary, not signed, and the local format shim fixes that defect;
- the main remaining BER problem is now higher-level: the runtime `bridge_rx_only` path still measures BER against an asynchronously running host-side cyclic burst, so reducing the residual `127 / 114` error floor likely requires either a self-timed FPGA TX/RX path (`bridge_txrx_mux`) or an explicit preamble/frame detector in the FPGA receive path.

That guidance is based on the live `2026-06-21` to `2026-06-23` probes:

- removing the gpreg clock monitor cleared the earlier `0x79040004` external-abort / `Bus error` symptom;
- reloading the new PL image through `fpga_manager` while Linux was already running left `gpreg` readable again, but standalone `iio_readdev` capture no longer refilled cleanly;
- a stricter stock-vs-runtime comparison on `2026-06-23` then proved that a fresh stock shell still supports both direct host `libiio Buffer.refill()` capture and short `iio_readdev` capture before any reload;
- that same comparison also proved that the runtime hot load breaks both host RX capture paths afterwards while `axi_gpreg` still answers and `rx_valid_count` stays at zero;
- the refined `bridge_rx_only` runtime witness on `2026-06-23` then added a raw RX-tap proof: even during host-driven stock TX, `gp_capture_debug` stayed `0`, so the bridge saw no `capture_in_valid` pulses, no non-zero `RX1` samples, and no measurable RX peak at all after the hot reload;
- after the manual RX-common re-init revived the fabric-side receive path, a fresh single-point runtime proof on `2026-06-23` showed that the full-frame `281 / 144 / 136` result is not caused by missing samples: the packed `GPREG5` decision witness reported recovered valid pulses and non-zero decision samples, but no negative decision sample and no recovered bit `1`, which means the live receiver is effectively producing an all-zero recovered bit stream;
- a stricter raw-sign witness (`docs/assets/lab120_runtime_capture_sign_single_point_live_20260623.json`) then proved that the bridge tap itself still never went negative: raw `RX1 I/Q` reached a full-scale unsigned range, but both `capture_i_negative_seen_any` and `capture_q_negative_seen_any` remained false;
- source inspection of `library/common/ad_datafmt.v` and `library/common/up_adc_channel.v` in the imported ADI HDL explained that result: with the default RX data-format controls left at zero, the bridge tap carries raw 12-bit offset-binary AD9361 samples in the low bits rather than signed two's-complement values;
- the bridge now corrects that locally in `bpsk_zynq_ber_gpreg_bridge.v` before feeding `bpsk_zynq_ber_top`, while preserving the raw-tap witness in `CAPTURE_DEBUG`;
- the live post-fix proof (`docs/assets/lab121_runtime_offset_binary_fix_single_point_live_20260623.json`) confirmed that the receive chain no longer collapses to an all-zero stream: negative decisions and recovered `1` bits now appear on hardware, and payload errors dropped from `136` to `131` at the same single point;
- the next tuned fresh-session sweeps then improved the best live point to `received_bits = 281`, `total_errors = 127`, `payload_errors = 114` at `start_offset = 34`, `tx_phase = 315 deg`, `rx_gain = 5 dB`; see `docs/assets/lab122_runtime_offset_binary_fix_phase_sweep_live_20260623.json`, `docs/assets/lab123_runtime_offset_binary_fix_tx_phase_sweep_live_20260623.json`, and `docs/assets/lab124_runtime_offset_binary_fix_gain_sweep_live_20260623.json`;
- the next self-timed `bridge_txrx_mux` runtime step proved that the course-owned TX/RX path can now complete a full frame without the old timeout behavior; see `docs/assets/lab125_runtime_bridge_txrx_self_timed_single_point_live_20260623.json`;
- a simple decision-axis experiment then showed that control-plane-selectable `I / -I / Q / -Q` matters on the live self-timed path: the exploratory mode sweep favored `neg-i` over the default `i`, while a follow-up clean single-point rerun remained full-frame but still session-sensitive; see `docs/assets/lab126_runtime_bridge_txrx_self_timed_mode_sweep_live_20260623.json` and `docs/assets/lab126_runtime_bridge_txrx_self_timed_neg_i_single_point_live_20260623.json`.
- manually booting Linux after a real U-Boot `fpga load` of the course bitstream showed that deleting the DAC DMA path from the PL shell causes a kernel panic in `axi_dmac_probe()`;
- after restoring the DAC DMA shell and the stale Linux DT fixups, the next remaining live blocker was AD9361 calibration timeout under the TX-override bitstream itself;
- the current debug step therefore keeps the live DAC FIFO path untouched and uses either `gpreg_only` or the new intermediate `bridge_rx_only` mode until AD9361 boot is stable again;
- rebuilding even the `vendor_only` shell from the recovered CLG400 sources still left AD9361 stuck in `Calibration TIMEOUT (0x244, 0x80)` during clean boot;
- the standalone vendor reference `../../ps/ad936x_no_os_reference/platform/hw/system_top.bit` remains the preferred source-correlated raw-bit proof candidate, but it still fails AD9361 clean boot both as raw `.bit` and as manual `.bit.bin` `fpga load`;
- the extracted `../../boot/sd_image/BOOT.bin` partition payload is now the only externally loaded boot-safe baseline demonstrated so far;
- source-level comparison against `ps/ad936x_no_os_reference/platform/hw/system_top.xsa` shows that the normalized pure-Tcl `vendor_only` flow is now blocked by four read-only or disabled derived parameters rather than missing whole modules;
- the saved vendor `zc702.xpr` snapshot, rebuilt through `../../rebuild_vendor_xpr_snapshot_mio_patch.tcl`, is still the preferred editable structural witness because it matches the vendor reference XSA structurally, but it is not yet a boot-safe RF baseline;
- the stock Linux device tree still described the removed `i2c@41600000` and `mwipcore@43c00000` PL nodes, so clean-boot bring-up also needs the U-Boot-side device-tree fixup above;
- attempting to recover the RX DMA path with Linux `unbind` / `bind` triggered a kernel oops in `dma_channel_rebalance()`.

## Intended first RF run

1. Keep AD9361 TX attenuation at the minimum output power setting available on the board.
2. Keep RX gain low and manual. Do not enable AGC for the first burst.
3. Use short frames only.
4. Confirm both the `axi_gpreg` ID and the bridge signature before transmitting.
5. If RX never reconstructs the full frame, the BER core exits through the sticky timeout bit instead of hanging forever.
6. Treat this overlay as discovery-only until the first live BER capture is documented.
