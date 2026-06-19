# Lab 11.7 - PS-side AXI-Lite BPSK bring-up

## Goal

Execute the smallest reproducible Processing System control sequence for the deterministic BPSK burst core:

```text
PS / software -> AXI-Lite registers -> framed BPSK BER core -> AD9363 discovery burst
```

This lab bridges:

- Lab 5.11, which defined and verified the AXI-Lite register contract;
- Lab 6.3, which fixed the AD9363 gain and frequency discipline for the first RF run;
- Block 11 hardware handoff, where one short burst must be launched safely and reproducibly.

## Engineering question

> What is the minimum PS-side sequence that should succeed before longer RF measurements or BER campaigns are attempted?

## Executable file

| File | Purpose |
|---|---|
| `blocks/block_11_integrated_sdr_project/python/lab_11_7_axi_lite_bpsk_bringup.py` | reads AXI-Lite `ID`, programs burst registers, launches one run, polls `busy/done`, reads BER counters |

## Local mock run

Run from the repository root:

```bash
python blocks/block_11_integrated_sdr_project/python/lab_11_7_axi_lite_bpsk_bringup.py \
  --backend mock \
  --max-total-errors 0 \
  --max-payload-errors 0 \
  --json-out docs/assets/lab117_axi_lite_bringup_mock.json
```

Expected local behavior:

- the script exits with code `0`;
- `busy_observed` and `done_observed` are both `true`;
- `received_bits == frame_bit_count`;
- `total_errors == 0`;
- `payload_errors == 0`.

## Real board run

On the Zynq Linux image, run as `root` or through `sudo`. Use the actual AXI-Lite base address from Vivado Address Editor, exported headers, or board handoff notes.

You can inspect an exported Vivado handoff file directly from this repository:

```bash
python tools/inspect_xsa_memmap.py hardware/7020_ad936x_sdr/ps/ad936x_no_os_reference/system_top.xsa
python tools/inspect_xsa_memmap.py path/to/your_regenerated_design.xsa --find bpsk --require-match
```

The helper also understands vendor ZIP bundles that contain a nested `system_top.xsa`, for example:

```bash
python tools/inspect_xsa_memmap.py E:\7020\7020_AD936X_SDR\Vivado2021.1\Driver_PL_PS\AD936X_PS.zip --find axi_ad9361
```

The current `ad936x_no_os_reference/system_top.xsa` export contains `axi_ad9361` and the two DMA windows, but it does **not** yet contain `bpsk_zynq_ber_axi_lite`. Until the custom modem IP is inserted into the block design and the XSA is regenerated, any `--base-addr` value below is only a placeholder example.

Vendor package note from `E:\7020`:

- the firmware bundle is Pluto-like and uses `root` / `analog`;
- the serial console guidance is `115200` baud;
- the bundled `uEnv.txt` sets `ipaddr=192.168.2.1` and `ipaddr_host=192.168.2.10`;
- companion README files in the same bundle also mention `192.168.1.10`.

That mismatch is exactly why the course flow should probe the active image first instead of assuming the vendor default IP.

Direct `/dev/mem` mapping:

```bash
sudo python blocks/block_11_integrated_sdr_project/python/lab_11_7_axi_lite_bpsk_bringup.py \
  --backend mmap \
  --base-addr 0x43C00000 \
  --frame-bit-count 281 \
  --preamble-count 25 \
  --start-offset 62 \
  --json-out reports/lab117_axi_lite_bringup.json
```

Fallback through the `devmem` utility:

```bash
sudo python blocks/block_11_integrated_sdr_project/python/lab_11_7_axi_lite_bpsk_bringup.py \
  --backend devmem \
  --base-addr 0x43C00000 \
  --frame-bit-count 281 \
  --preamble-count 25 \
  --start-offset 62 \
  --json-out reports/lab117_axi_lite_bringup.json
```

Host-side remote check over Ethernet, without copying the script to the board:

```bash
python blocks/block_11_integrated_sdr_project/python/lab_11_7_axi_lite_bpsk_bringup.py \
  --backend ssh-devmem \
  --ssh-host 192.168.40.1 \
  --ssh-user root \
  --ssh-password analog \
  --base-addr 0x43C00000 \
  --frame-bit-count 281 \
  --preamble-count 25 \
  --start-offset 62
```

Live board note on **2026-06-19**:

- the stock course-clean image answered over IIO at `192.168.40.1`;
- the live device tree declared `mwipcore@43c00000` with `compatible = "mathworks,mwipcore-axi4lite-v1.00"`;
- direct register reads to `0x43C00000 + {0x00..0x1C}` returned `Bus error`, while ADI reference windows at `0x79020000`, `0x79024000`, `0x7C400000`, and `0x7C420000` were readable.

That means the current board image is **not** ready for Lab 11.7 bring-up yet: the address is declared, but the loaded PL design does not expose a working slave at that window.

## Backends

| Backend | Intended use |
|---|---|
| `mock` | local CI-friendly self-check without hardware |
| `mmap` | direct Linux `/dev/mem` access on the board |
| `devmem` | fallback when `/dev/mem` mapping is inconvenient but `devmem` exists |
| `ssh-devmem` | host-side remote `devmem` access over SSH to a live Linux board |

## Register contract

This lab uses the same map as Lab 5.11:

| Offset | Name | Meaning |
|---|---|---|
| `0x00` | `CONTROL_STATUS` | write bit `0` to start, read bit `1` for `busy`, read/write bit `2` for sticky `done` |
| `0x04` | `FRAME_BIT_COUNT` | total transmitted and compared bits |
| `0x08` | `PREAMBLE_COUNT` | preamble bits excluded from payload BER |
| `0x0C` | `START_OFFSET` | deterministic sample index for decisions |
| `0x10` | `RECEIVED_BITS` | recovered bits after the burst |
| `0x14` | `TOTAL_ERRORS` | all bit errors |
| `0x18` | `PAYLOAD_ERRORS` | payload-only bit errors |
| `0x1C` | `ID` | expected identification word `0x4250534B` |

## First discovery-burst order

1. Probe the AD9363 context with Lab 6.3 or `iio_attr`.
2. Keep TX power at minimum and RX gain low/manual.
3. Disable AGC for the first burst.
4. Read `ID` first through AXI-Lite.
5. Program `FRAME_BIT_COUNT`, `PREAMBLE_COUNT`, and `START_OFFSET`.
6. Launch one short burst.
7. Poll `busy` and `done`.
8. Read BER counters and clear sticky `done`.

## Generated artifact

The mock run writes:

```text
docs/assets/lab117_axi_lite_bringup_mock.json
```

The JSON report captures the programmed configuration, observed status bits, BER counters, and a final register snapshot.

## Report checklist

- [ ] Record the actual AXI-Lite base address used on hardware.
- [ ] Show one successful `ID` readback.
- [ ] Show programmed `FRAME_BIT_COUNT`, `PREAMBLE_COUNT`, and `START_OFFSET`.
- [ ] State whether `busy` and `done` were both observed.
- [ ] Record `RECEIVED_BITS`, `TOTAL_ERRORS`, and `PAYLOAD_ERRORS`.
- [ ] State whether the first run is discovery-only or already BER-grade.
- [ ] Link the run to the AD9363 settings table from Lab 6.3.

## Engineering conclusion template

```text
The PS-side AXI-Lite bring-up path is ready / not ready.
The core ID readback is ______, the burst status sequence is ______, and the BER counters are ______.
The next step is ______.
```
