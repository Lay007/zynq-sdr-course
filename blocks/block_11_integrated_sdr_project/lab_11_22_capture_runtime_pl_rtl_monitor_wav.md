# Lab 11.22 — Capture RTL-SDR monitor WAV during runtime/PL BPSK bring-up

## Objective

Run the same RTL-SDR external monitoring approach as Lab 11.21, but with the
ZynqSDR operating under the **runtime course overlay** (`bridge_txrx_mux`)
instead of the stock shell. The goal is to confirm whether the PL BPSK TX path
actually radiates an RF signal even when `rx_valid_count = 0` — which would
isolate the failure to the RX side only.

## Engineering question

> If `tx_valid_count > 0` in the PL overlay but the RTL-SDR monitor sees no
> signal, then the PL TX DAC path is broken. If the RTL-SDR does see a signal,
> then only the PL RX path needs to be fixed.

## Hardware setup

Same physical layout as Lab 11.21:

```text
ZynqSDR TX1 antenna  ─── (air gap, ~1–5 m) ───  RTL-SDR antenna
```

The overlay under test is `bridge_txrx_mux.wordswap.bit.bin`.

## Files

| Path | Purpose |
|---|---|
| `blocks/block_11_integrated_sdr_project/python/lab_11_22_capture_runtime_pl_rtl_monitor_wav.py` | load runtime overlay, start PL bring-up, simultaneously capture RTL-SDR WAV |

## Run

```bash
python blocks/block_11_integrated_sdr_project/python/\
lab_11_22_capture_runtime_pl_rtl_monitor_wav.py \
  --bit-bin tmp/bridge_txrx_mux.wordswap.bit.bin \
  --center-frequency-hz 915000000 \
  --sample-rate-hz 2400000 \
  --tuner-gain-db10 200 \
  --capture-duration-s 10.0 \
  --wav-out datasets/lab11_22_runtime_rtl_monitor/capture_live.wav \
  --manifest-out datasets/lab11_22_runtime_rtl_monitor/manifest_live.yaml \
  --run-tag runtime_pl_bpsk_rtl_monitor
```

The script:

1. loads the runtime overlay through `fpga_manager`;
2. verifies `axi_gpreg` ID (0x4250534B);
3. configures the AD9361 TX/RX at 915 MHz;
4. asserts `burst_start`;
5. simultaneously records RTL-SDR WAV for `--capture-duration-s` seconds;
6. reads final `tx_valid_count`, `rx_valid_count`, `received_bits`;
7. restores AD9361, saves WAV and manifest, optionally reboots.

## Parallel monitoring thread

The RTL-SDR capture runs in a background thread while the main thread manages
the PL bring-up sequence. Thread synchronization is via a `threading.Event`:
the capture thread records from the moment `burst_start` is asserted until the
event is set at the end of `--capture-duration-s`.

## Live result on 2026-06-23 — corrected

> **Correction.** An earlier version of this section said that the offline analysis "detected the BPSK
> preamble and measured BER = 0 / EVM ≈ 56 %" and concluded that "the PL BPSK TX path radiates correctly".
> The committed analysis output does not support that. The capture of the runtime PL run scores
> **105 bit errors out of 281 (BER 0.37)**, EVM ≈ 820 %, and a preamble correlation of 0.13 — the
> signature of no BPSK signal at all ([metrics](/zynq-sdr-course/assets/lab1120_lab11_22_runtime_pl_rtl_monitor_live_20260624_runtime_pl_a_live_20260624_runtime_pl_a_metrics.json)).

What the run did show is the gpreg pattern `tx_valid_count > 0`, `rx_valid_count = 0`. The counters
prove that the PL modem produced samples; they do not prove that the samples reached the DAC. Lab 11.26
found that they did not: after the overlay reload the AD9361 DAC core comes up in DDS-only mode and
ignores the PL stream ([Lab 11.26](/zynq-sdr-course/en/labs/lab-11-26-runtime-dds-bypass-bpsk-ota/)).

The lesson is the one this page originally missed: a counter inside the FPGA is not evidence of a
radiated signal. Only the independent receiver can say that, and here it said "no".

## Report checklist

- [ ] Confirm `axi_gpreg` ID before capture.
- [ ] Record `tx_valid_count` at end of capture.
- [ ] Record `rx_valid_count` at end of capture.
- [ ] Attach RTL-SDR WAV manifest.
- [ ] Cross-reference with Lab 11.20 offline BER on this WAV.

## Engineering conclusion template

```text
The runtime bridge_txrx_mux overlay was loaded and axi_gpreg ID = 0x____.
During a ____-second RTL-SDR capture at ____ MHz, tx_valid_count = ____ and
rx_valid_count = ____. Offline Lab 11.20 BER result on this WAV: ____,
EVM = ____ %. Conclusion: PL TX is / is not radiating. The RX starvation is /
is not isolated to the AD9361→PL DMA path.
```
