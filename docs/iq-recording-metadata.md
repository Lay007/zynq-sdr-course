# IQ recording metadata guide

Real SDR experiments are useful only when the captured IQ data can be interpreted later. Every IQ recording should be stored together with a small metadata file.

## Why metadata matters

An IQ file without metadata is almost impossible to reproduce. The same binary stream can represent different sample rates, center frequencies, gains, channel bandwidths or numeric formats.

The minimum rule:

> Every IQ capture must have a matching `.json` or `.yaml` metadata file with the same base name.

Example:

```text
measurements/
  tone_915mhz_2026-05-03.ci16
  tone_915mhz_2026-05-03.json
```

## Recommended JSON format

```json
{
  "recording_id": "tone_915mhz_2026-05-03",
  "description": "Single-tone RF observation using RTL-SDR",
  "created_utc": "2026-05-03T10:00:00Z",
  "operator": "",
  "hardware": {
    "tx_board": "Zynq-7020 + AD9363",
    "rx_device": "RTL-SDR V3 Pro",
    "rf_path": "coax + attenuator",
    "attenuation_db": 30
  },
  "rf": {
    "tx_center_frequency_hz": 915000000,
    "rx_center_frequency_hz": 915000000,
    "tx_gain_db": -20,
    "rx_gain_db": 20,
    "rf_bandwidth_hz": 2000000
  },
  "sampling": {
    "sample_rate_hz": 2400000,
    "sample_count": 1048576,
    "iq_format": "ci16",
    "endianness": "little",
    "i_first": true
  },
  "signal": {
    "type": "tone",
    "expected_offset_hz": 100000,
    "modulation": "none"
  },
  "processing": {
    "fft_length": 65536,
    "window": "hann",
    "normalization": "amplitude"
  },
  "quality_notes": {
    "clipping_observed": false,
    "overload_warning": false,
    "comments": ""
  }
}
```

## Required fields

| Group | Field | Why it is needed |
|---|---|---|
| Recording | `recording_id` | Stable reference in reports |
| Hardware | `tx_board`, `rx_device` | Reproduce the measurement chain |
| RF | center frequency, gain, bandwidth | Interpret spectrum correctly |
| Sampling | sample rate, format, sample count | Decode binary IQ stream |
| Signal | signal type and expected offset | Validate the experiment |
| Processing | FFT length and window | Reproduce plots |

## Naming convention

Use readable names:

```text
<experiment>_<center-frequency>_<sample-rate>_<date>.<format>
```

Examples:

```text
tone_915mhz_2p4msps_2026-05-03.ci16
qpsk_868mhz_4msps_2026-05-03.ci16
fir_replay_baseband_1msps_2026-05-03.wav
```

## Supported IQ formats

| Format | Meaning | Typical use |
|---|---|---|
| `cf32` | complex float32 IQ | MATLAB/Python analysis |
| `ci16` | interleaved int16 IQ | SDR recordings and FPGA replay |
| `cu8` | unsigned 8-bit IQ | RTL-SDR raw captures |
| `wav` | WAV container with IQ channels | HDSDR-compatible exchange |

## Report checklist

Every lab report that uses real IQ data should state:

- where the IQ file came from;
- what hardware produced it;
- exact center frequency and sample rate;
- whether clipping or overload was observed;
- which script generated the plots;
- which metrics were computed from the recording.
