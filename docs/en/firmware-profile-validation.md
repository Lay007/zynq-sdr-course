# Firmware profile validation

This procedure implements the first, offline stage of [issue #81](https://github.com/Lay007/zynq-sdr-course/issues/81)
and [ADR 0004](../adr/0004-zynqsdr-firmware-profiles.md).
It prepares evidence for the Zynq-7020/AD936x bench; it does not switch firmware.
[Русская версия](../ru/firmware-profile-validation.md).

## Evidence gates

| Evidence | What it establishes | What remains open |
| --- | --- | --- |
| Manifest and SHA-256 match | Listed archive files have the recorded content | External dependencies, boot compatibility |
| LFS pointer oid/size match | Recorded object identity | Downloaded payload integrity |
| Static `uEnv.txt` inventory | Declared file paths and duplicate assignments | Executed boot path and persistent U-Boot defaults |
| Live IIO enumeration | Devices, channels and readable configured attributes at that time | Physical clocks, DMA transfers, FPGA identity, RF |
| Boot and rollback record per board | Tested boot/recovery sequence for that board and composition | Other boards or image versions |
| Protected RF experiment | Measured performance under recorded conditions | Other gains, frequencies and RF paths |

Keep `archive_status`, `boot_tested`, `rf_measured` and `currently_deployed` separate.
An old deployment record does not identify the image running today.
Operator-supplied board/profile names are declarations, not automatic detection.

## Archive candidates

The private artifact repository owns the manifest references, checksums, registry
and dated inventory. Public course sources contain the procedure and synthetic examples.

| Profile candidate | Composition still to establish |
| --- | --- |
| `vendor-pluto` | Complete vendor boot dependencies and per-board baseline |
| `vendor-zynqsdr-legacy` | Selection of root/nested SD variant and missing dependencies |
| `course-fpga` | Complete boot set and reproducible PL/clock/reset sequence |
| `qpsk-modem` | Linux/DTB/boot composition around the archived FPGA image |
| `display-demo` | Image, electrical interface and display validation |

The offline inventory on 2026-11-06 checked 70 materialized files across eight
selected manifests: recorded sizes and SHA-256 matched. This is archive evidence.
The historical course boot set requires `uImage`, which is absent from that set;
SD candidates also declare missing kernel paths. Some declare other absent paths.
No candidate is promoted to a tested recovery image by this inventory.
Locate the original kernel and its provenance, or define and test a new boot
composition separately. Do not substitute an arbitrary kernel or regenerate
historical hashes to make a check pass.

From the private repository root, run these commands in order:

1. `python -m unittest discover -s tests -v`
2. `python verify_manifests.py --quiet --lfs-pointers`
3. `python verify_profiles.py --lfs-pointers --json-out firmware-profiles/inventory-local.json`

Pointer acceptance is useful for CI. Repeat the selected profile check without
`--lfs-pointers` against materialized payloads before calling it a byte check.
The private tool can use `--payload-root` for a separate materialized checkout.
Its exit status covers registry/archive integrity; boot blockers remain visible
in the report even when integrity checks pass. `uEnv.txt` is parsed as text,
using the last assignment for duplicate keys; no commands are executed.
Declared paths are interpreted relative to each archived SD variant, not as
proof of the active boot flow.

## Offline observation report

Lab 6.3 can replay its saved JSON without importing libiio or contacting a board.
Run from the public course root; keep outputs in the private evidence directory:

```bash
python blocks/block_06_rf_frontend_and_ad9363/python/lab_6_3_probe_iio_context.py --probe-json templates/iio_probe.synthetic.json --board-id synthetic-A --profile-id vendor-pluto --profile-report ../zynq-sdr-course-artifacts/evidence/issue81/synthetic-profile.json
```

This example has no devices and no observation timestamp because it is synthetic.
For a real saved probe, replace the input path and declared identifiers.
The report records `source: saved-probe`, preserves the original observation time
(or `null` for legacy snapshots), and records report generation time separately.
Replay does not establish current deployment.

## Later bench stages

These stages require access to the identified board and a reviewed recovery/RF setup.
They were **not performed** by the offline inventory.

1. Record board identity, boot mode, serial boot log, Linux identity, FPGA image
   identity and active boot files. Keep raw IP/MAC/configuration data private.
2. Once normal IIO attribute reads are appropriate for that board, obtain a live
   Lab 6.3 observation with explicit URI. For example, replace the example host:

   ```bash
   python blocks/block_06_rf_frontend_and_ad9363/python/lab_6_3_probe_iio_context.py --uri ip:BOARD_HOST --board-id A --profile-id vendor-pluto --json-out ../zynq-sdr-course-artifacts/evidence/issue81/A-probe.json --profile-report ../zynq-sdr-course-artifacts/evidence/issue81/A-profile.json
   ```

   Profile-report mode excludes debug attribute reads. It reads normal attributes
   without creating buffers or writing configuration. It also reads TX LO
   `powerdown` where available; it does **not** mute TX or establish receiver safety.
   Read errors and absent attributes are observations, not successful checks.
3. Establish a tested rollback for **each** board on a separate SD card while
   retaining the original medium. The A/B QSPI archives differ; a dump is not
   a universal recovery recipe. This procedure contains no QSPI write commands.
4. Test boot, PL reset, actual sample clock and RX DMA separately. Record exact
   file hashes, serial logs, sample counts, timeouts and errors. An RX capture
   tool can change configuration and allocate buffers; it is a separate operation.
5. Only then perform RF measurements with the documented frequency plan, gains,
   attenuation, receiver limits and IQ metadata in the [RF safety guide](../rf-safety.md).
   Use a reviewed protected path; no unverified direct TX-to-RX connection.

## Software-QPSK versus PL-QPSK comparison protocol

Before measurement, freeze the reference model, fixed-point formats and HDL
revision. Use the same payload/seed, modulation mapping, preamble, symbol/sample
rates, samples per symbol, RRC taps/roll-off and normalization. Record differences
in quantization, clipping and transport rather than treating them as equivalent.

For each run record the board/profile and image hashes, LO/bandwidth, RX/TX gains,
RF path/attenuation, sample format/order/scale, requested and received sample
counts, DMA errors, clock/reset state and receiver synchronization settings.
Define latency endpoints and units before timing; report framing/transport
overhead separately. Compare packet counts, BER/PER and EVM only under matched
conditions. Include dropped and unsynchronized packets in PER; report the BER
denominator and decoded coverage separately because missing bits have no observed errors.
Keep reference-model, RTL, board-loopback and measured-RF results in separate
columns with links to raw private evidence and a sanitized public report.
No performance figures are supplied by this protocol.
