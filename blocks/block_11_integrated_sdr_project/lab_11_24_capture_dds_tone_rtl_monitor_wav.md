# Lab 11.24 - Capture RTL-SDR monitor WAV during stock/runtime DDS-tone TX

## Objective

Use the RTL-SDR as an external monitor to capture the DDS-generated single tone
from the ZynqSDR `cf-ad9361-dds-core-lpc` device in both **stock-shell** and
**runtime overlay** modes, and save a WAV recording of each for offline
frequency-plan verification.

DDS tones are simpler to confirm than BPSK bursts because the expected signal
is a single spectral peak at a known offset from the carrier. This makes
them a clean RF sanity check that can run without any PL modem logic.

## Why this lab

After confirming BPSK TX viability in Labs 11.21–11.22, the next question is:

> Does the DDS tone behave differently between stock-shell and runtime-overlay
> modes? Specifically, does the runtime `fpga_manager` reload affect the DDS
> tone path (frequency, amplitude, tone enable)?

If the tone shifts frequency or disappears after an overlay reload, it
indicates that the AD9361 DDS peripheral state is not restored correctly by
the runtime boot sequence.

## Hardware setup

```
ZynqSDR TX1 antenna ─── (air gap, ~1–5 m) ─── RTL-SDR antenna
```

The DDS is configured to generate a tone at **+50 kHz** from the LO (915 MHz).
Expected RTL-SDR peak: 915.050 MHz.

## Files

| Path | Purpose |
|---|---|
| `blocks/block_11_integrated_sdr_project/python/lab_11_24_capture_dds_tone_rtl_monitor_wav.py` | configure DDS, capture RTL-SDR WAV in stock and/or runtime mode, save manifest |

## Run (stock-shell only)

```bash
python blocks/block_11_integrated_sdr_project/python/\
lab_11_24_capture_dds_tone_rtl_monitor_wav.py \
  --mode stock \
  --center-frequency-hz 915000000 \
  --tone-offset-hz 50000 \
  --sample-rate-hz 2400000 \
  --tuner-gain-db10 200 \
  --capture-duration-s 3.0 \
  --wav-out datasets/lab11_24_dds_tone/stock_tone_50kHz.wav \
  --manifest-out datasets/lab11_24_dds_tone/stock_manifest.yaml
```

## Run (runtime mode)

```bash
python blocks/block_11_integrated_sdr_project/python/\
lab_11_24_capture_dds_tone_rtl_monitor_wav.py \
  --mode runtime \
  --bit-bin tmp/bridge_txrx_mux.wordswap.bit.bin \
  --center-frequency-hz 915000000 \
  --tone-offset-hz 50000 \
  --sample-rate-hz 2400000 \
  --tuner-gain-db10 200 \
  --capture-duration-s 3.0 \
  --wav-out datasets/lab11_24_dds_tone/runtime_tone_50kHz.wav \
  --manifest-out datasets/lab11_24_dds_tone/runtime_manifest.yaml
```

## Expected offline verification

After capturing, analyze both WAVs with the Block 9 reader and compare peak
locations:

```bash
python blocks/block_09_recording_and_analysis_tools/python/lab_9_4_read_wav_iq_and_analyze.py \
  --manifest datasets/lab11_24_dds_tone/stock_manifest.yaml

python blocks/block_09_recording_and_analysis_tools/python/lab_9_4_read_wav_iq_and_analyze.py \
  --manifest datasets/lab11_24_dds_tone/runtime_manifest.yaml
```

Expect the FFT peak at **+50 kHz** from center in both cases.

## Live result on 2026-06-24

Both stock-shell and runtime-overlay DDS tones were captured on the RTL-SDR.
Peak frequency confirmed at +50 kHz from 915 MHz in both cases. Amplitude
difference between stock and runtime modes: < 1 dB (within RTL-SDR measurement
uncertainty). DDS tone path is not affected by the runtime overlay reload.

This confirms that the AD9361 DDS peripheral is correctly restored by the
runtime boot sequence, and that any remaining bring-up problem is limited to
the PL BPSK RX path.

## Report checklist

- [ ] Attach WAV manifest for stock-shell capture.
- [ ] Attach WAV manifest for runtime capture.
- [ ] Record FFT peak location in each mode.
- [ ] Record peak amplitude difference between modes.
- [ ] State whether DDS tone path is affected by overlay reload.

## Engineering conclusion template

```text
DDS tone at +____ kHz from ____ MHz was captured by RTL-SDR in both stock-shell
and runtime-overlay modes. Stock-shell peak: ____ kHz (offset from LO). Runtime
peak: ____ kHz. Amplitude difference: ____ dB. The DDS tone path is / is not
affected by the runtime fpga_manager reload because ______.
```
