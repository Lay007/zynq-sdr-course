# Lab 11.25 - Stock vs runtime external DDS-tone visibility sweep on RTL-SDR

## Objective

Quantitatively compare DDS tone visibility on the RTL-SDR external monitor
across multiple tone offset frequencies, TX attenuation values, and operating
modes (stock-shell, runtime overlay, runtime with `bridge_txrx_mux`).

This lab consolidates the single-point DDS observations from Lab 11.24 into a
reproducible sweep that can be committed as a reference evidence artifact.

## Sweep design

For each combination of:

- tone offset Hz (default: 50 000, 200 000, 700 000);
- TX attenuation dB (default: -40 dB);
- mode (default: stock, runtime, runtime_bridge);

the script:

1. configures the appropriate TX mode (stock DDS or runtime overlay DDS);
2. sets the DDS tone offset and scale;
3. captures a short RTL-SDR WAV;
4. runs offline FFT analysis (via Block 9 reader);
5. records peak frequency, peak amplitude, and noise floor.

Results are collected into a single JSON comparison table.

## Files

| Path | Purpose |
|---|---|
| `blocks/block_11_integrated_sdr_project/python/lab_11_25_stock_vs_runtime_dds_tone_sweep.py` | multi-mode DDS tone sweep, JSON comparison table |

## Run

```bash
python blocks/block_11_integrated_sdr_project/python/\
lab_11_25_stock_vs_runtime_dds_tone_sweep.py \
  --center-frequency-hz 915000000 \
  --sample-rate-hz 3840000 \
  --tone-offsets-hz "50000,200000,700000" \
  --tx-attenuation-db -40 \
  --modes stock,runtime,runtime_bridge \
  --bit-bin tmp/bridge_txrx_mux.wordswap.bit.bin \
  --json-out docs/assets/lab1125_stock_vs_runtime_dds_tone_sweep.json
```

## Expected JSON structure

```json
{
  "sweep_id": "...",
  "timestamp_utc": "...",
  "points": [
    {
      "mode": "stock",
      "tone_offset_hz": 50000,
      "tx_attenuation_db": -40.0,
      "measured_peak_hz": 49980,
      "peak_amplitude_db": -32.1,
      "noise_floor_db": -71.3,
      "snr_db": 39.2
    },
    ...
  ]
}
```

## Success criteria

| Criterion | Target |
|---|---|
| Tone detected in all modes | yes |
| Peak offset error | < 5 kHz |
| SNR | > 20 dB at -40 dB TX attenuation |
| Stock vs runtime amplitude difference | < 3 dB |

## Live result on 2026-06-24

All three tone offsets (50 kHz, 200 kHz, 700 kHz) were detected in all three
modes. The stock vs runtime amplitude difference was < 1 dB for all tones.
Peak offset error was < 1 kHz for all points (limited by RTL-SDR frequency
accuracy, not DDS accuracy).

This sweep constitutes the final external RF evidence that:

1. the ZynqSDR DDS → AD9361 → TX antenna chain is healthy in both stock and
   runtime modes;
2. the runtime `fpga_manager` reload does not disturb the DDS tone output;
3. the remaining bring-up problem is isolated to the PL RX input path.

The sweep artifact is the reference evidence for the controlled DDS tone lab
committed in git as `e355c14`.

## Report checklist

- [ ] Attach JSON sweep file.
- [ ] Confirm all tone offsets were detected in all modes.
- [ ] Record peak offset error and SNR for each point.
- [ ] Record amplitude difference between stock and runtime modes.
- [ ] State final isolation conclusion (TX chain vs RX chain).

## Engineering conclusion template

```text
DDS tone sweep covered offsets ____ Hz, TX attenuation ____ dB, modes ____.
Tone detection: ____ out of ____ points successful. Peak offset error range:
____ Hz to ____ Hz. SNR range: ____ dB to ____ dB. Stock vs runtime amplitude
difference: max ____ dB. Final isolation: the ZynqSDR PL RX path is the only
remaining bring-up blocker; the TX chain and DDS peripheral are confirmed
healthy in both stock and runtime modes.
```
