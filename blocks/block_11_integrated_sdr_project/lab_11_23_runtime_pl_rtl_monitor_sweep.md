# Lab 11.23 - Focused runtime/PL RTL-SDR monitor sweep around the live BPSK point

## Objective

Perform a short parametric sweep of TX attenuation and RX gain around the
operating point confirmed in Lab 11.22, using the RTL-SDR as an external
monitor, and record how the offline BER and EVM evolve with each setting.

This turns the Lab 11.22 single-point measurement into a small characterization
table, useful for choosing the best TX power and RTL-SDR gain for reliable
external monitoring of the runtime PL BPSK TX during future bring-up sessions.

## Sweep design

For each `(tx_attenuation_db, rtl_tuner_gain_db10)` combination:

1. Load the `bridge_txrx_mux` overlay (once at the start, not per iteration).
2. Reconfigure AD9361 TX attenuation via network IIO.
3. Assert `burst_start`.
4. Record RTL-SDR WAV for `--capture-duration-s` seconds.
5. Run offline BER / EVM analysis (Lab 11.20 code, called as library).
6. Collect `tx_valid_count`, `rx_valid_count`, `received_bits`.
7. Append result to JSON.

Default sweep:

```text
tx_attenuation_db  : -30, -40, -50, -60
rtl_tuner_gain_db10: 100, 200, 300  (= 10, 20, 30 dB)
```

Total: 12 points × ~5 s each ≈ ~1 minute.

## Files

| Path | Purpose |
|---|---|
| `blocks/block_11_integrated_sdr_project/python/lab_11_23_runtime_pl_rtl_monitor_sweep.py` | parametric sweep, per-point WAV, JSON table |

## Run

```bash
python blocks/block_11_integrated_sdr_project/python/\
lab_11_23_runtime_pl_rtl_monitor_sweep.py \
  --bit-bin tmp/bridge_txrx_mux.wordswap.bit.bin \
  --center-frequency-hz 915000000 \
  --tx-attenuations "-30,-40,-50,-60" \
  --rtl-gains "100,200,300" \
  --capture-duration-s 5.0 \
  --json-out docs/assets/lab1123_runtime_rtl_sweep.json
```

## Expected outputs

| File | Content |
|---|---|
| `docs/assets/lab1123_runtime_rtl_sweep.json` | BER/EVM table indexed by TX attenuation and RTL gain |
| `tmp/lab1123/point_<i>_<tag>.wav` | per-point RTL-SDR WAV (optional, `--keep-wav`) |

## Interpreting the result

| BER trend | Interpretation |
|---|---|
| BER = 0 at most points | OTA link is robust; TX power is sufficient |
| BER rises sharply at high TX attenuation | link budget limit found |
| BER non-zero even at lowest TX attenuation | RRC filter or timing recovery issue |

## Live result on 2026-06-23

The sweep confirmed BER = 0 for TX attenuation values down to -60 dB (the
lowest tested) with RTL-SDR gain ≥ 200 (20 dB). EVM ranged from 52 % to
60 % across the sweep, consistent with the single-point result from Lab 11.22.

Practical operating point chosen for subsequent monitoring labs:
- TX attenuation: **-50 dB**
- RTL-SDR tuner gain: **200** (20 dB)

## Report checklist

- [ ] Attach JSON sweep table.
- [ ] Identify the TX attenuation / RTL gain pair that gives BER = 0.
- [ ] Note EVM range across sweep.
- [ ] State recommended operating point for subsequent labs.

## Engineering conclusion template

```text
The focused RTL-SDR sweep covered TX attenuation values ____ dB and RTL tuner
gains ____. BER = 0 was observed for ____ out of ____ tested combinations.
EVM ranged from ____ % to ____ %. Recommended operating point: TX attenuation
= ____ dB, RTL gain = ____ dB.
```
