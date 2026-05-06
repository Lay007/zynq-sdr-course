# Lab 6.3 — AD9363 Settings and iio_attr Quick Reference

## Goal

Create a reproducible checklist for configuring an AD9363-based RF frontend and documenting the exact settings used during an SDR experiment.

The lab answers the practical question:

> Which AD9363 parameters must be recorded and controlled so that an RF measurement can be repeated later?

## Engineering context

In a real SDR experiment, the observed signal depends not only on DSP code. It also depends on RF frontend settings:

- LO frequency;
- RF bandwidth;
- sampling frequency;
- gain mode;
- hardware gain;
- enabled channels;
- analog filter state;
- external attenuation;
- AGC/manual gain behaviour.

If these settings are missing, the IQ recording is not reproducible.

## Typical IIO device naming

Exact names depend on the board image and Linux/IIO configuration. Common names are:

```text
ad9361-phy
cf-ad9361-lpc
cf-ad9361-dds-core-lpc
```

Some boards expose an AD9363 transceiver through an `ad9361-phy` compatible IIO device name. Always inspect the available devices on your system.

## Discovery commands

List IIO devices:

```bash
iio_info -s
```

Inspect device attributes:

```bash
iio_attr -d ad9361-phy
```

Inspect channel attributes:

```bash
iio_attr -c ad9361-phy
```

Inspect one channel:

```bash
iio_attr -c ad9361-phy voltage0
```

## Common RX parameters

| Purpose | Example command | Notes |
|---|---|---|
| RX LO frequency | `iio_attr -c ad9361-phy altvoltage0 frequency 915000000` | channel name may differ |
| RX RF bandwidth | `iio_attr -c ad9361-phy voltage0 rf_bandwidth 2000000` | Hz |
| RX sampling frequency | `iio_attr -c ad9361-phy voltage0 sampling_frequency 2400000` | Hz |
| RX gain control mode | `iio_attr -c ad9361-phy voltage0 gain_control_mode manual` | prefer manual for measurements |
| RX hardware gain | `iio_attr -c ad9361-phy voltage0 hardwaregain 10` | dB, range depends on hardware |

## Common TX parameters

| Purpose | Example command | Notes |
|---|---|---|
| TX LO frequency | `iio_attr -c ad9361-phy altvoltage1 frequency 915000000` | channel name may differ |
| TX RF bandwidth | `iio_attr -c ad9361-phy voltage0 rf_bandwidth 2000000` | output channel naming may differ |
| TX sampling frequency | `iio_attr -c ad9361-phy voltage0 sampling_frequency 2400000` | check TX device/channel |
| TX attenuation / gain | `iio_attr -c ad9361-phy voltage0 hardwaregain -20` | sign/range is board dependent |

!!! note "Board-specific names"
    The exact channel names for RX/TX LO and voltage channels may differ. Treat the commands above as a checklist pattern, not as a guaranteed universal command set.

## Minimal configuration checklist

Before capture or transmission, record:

| Field | Value |
|---|---|
| Board name |  |
| Linux image / firmware |  |
| IIO context URI |  |
| PHY device name |  |
| RX LO frequency |  |
| TX LO frequency |  |
| RX sample rate |  |
| TX sample rate |  |
| RX RF bandwidth |  |
| TX RF bandwidth |  |
| RX gain mode |  |
| RX hardware gain |  |
| TX attenuation/gain |  |
| External attenuation |  |
| Signal type |  |
| Expected baseband offset |  |

## Safe configuration procedure

1. Connect attenuator before enabling TX.
2. Use low TX level / high TX attenuation.
3. Use manual RX gain for repeatability.
4. Set LO frequencies.
5. Set sample rates.
6. Set RF bandwidths.
7. Generate a low-level single tone.
8. Observe spectrum for overload.
9. Save settings and IQ metadata.
10. Only then proceed to modulation experiments.

## Example session log

```bash
# Discover devices
iio_info -s

# Inspect the PHY
iio_attr -d ad9361-phy

# Set center frequency examples
iio_attr -c ad9361-phy altvoltage0 frequency 915000000
iio_attr -c ad9361-phy altvoltage1 frequency 915000000

# Set bandwidth and sample rate examples
iio_attr -c ad9361-phy voltage0 rf_bandwidth 2000000
iio_attr -c ad9361-phy voltage0 sampling_frequency 2400000

# Set manual gain example
iio_attr -c ad9361-phy voltage0 gain_control_mode manual
iio_attr -c ad9361-phy voltage0 hardwaregain 10
```

## What to include in the report

- exact commands used;
- command outputs or screenshots;
- frequency plan from Lab 6.1;
- gain plan from Lab 6.2;
- IQ metadata file;
- spectrum screenshot or generated FFT;
- overload check conclusion.

## Engineering conclusion template

```text
The AD9363 frontend was configured with RX LO = ____ MHz, TX LO = ____ MHz,
RX sample rate = ____ MS/s, RF bandwidth = ____ MHz and RX gain mode = ____.
The settings were recorded through iio_attr and linked to the IQ metadata file.
The observed spectrum confirms / does not confirm the expected RF configuration because ______.
```
