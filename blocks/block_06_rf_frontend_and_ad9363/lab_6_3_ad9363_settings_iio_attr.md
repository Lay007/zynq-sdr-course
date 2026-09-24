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

## Host-side Python probe

For a reproducible host-side check, the repository also includes:

```bash
python blocks/block_06_rf_frontend_and_ad9363/python/lab_6_3_probe_iio_context.py \
  --uri ip:192.168.40.1 \
  --json-out docs/assets/lab63_zynq_iio_probe.json
```

The script opens the remote IIO context, enumerates devices and channels, and
prints a compact AD9361 summary with RX/TX LO, bandwidth, sample rate, and gain
settings. On Windows it will also try the default `IIO Oscilloscope` install
path for `libiio.dll`.

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

## What to expect (a real probe of the course board)

`docs/assets/lab63_zynq_iio_probe_live.json` is the committed output of `lab_6_3_probe_iio_context.py` against the course board at `ip:192.168.40.1`, taken before any lab configuration:

| Attribute (probe JSON) | Value | Meaning |
|---|---|---|
| `hw_model` | FISH Ball PlutoSDR Rev.A (Z7020-AD9361) | the course board, stock Linux 5.15 |
| devices | `ad9361-phy`, `xadc`, `cf-ad9361-dds-core-lpc`, `cf-ad9361-lpc` | PHY control, on-chip temperature/voltage monitor, TX DMA/DDS core, RX DMA core |
| `altvoltage0` (RX LO) frequency | 2 400 000 000 | 2.4 GHz |
| `altvoltage1` (TX LO) frequency / `powerdown` | 2 400 000 000 / **1** | TX LO is switched off |
| `voltage0` in: `sampling_frequency` / `rf_bandwidth` | 30 720 000 / 18 000 000 | 30.72 MS/s, 18 MHz |
| `voltage0` in: `gain_control_mode` / `hardwaregain` | slow_attack / 71 dB | AGC at maximum gain: no signal present |
| `voltage0` out: `hardwaregain` | -89.75 dB | maximum TX attenuation |
| RX / TX port | A_BALANCED / A | |

- **This is a safe idle state, not a working one.** TX is at maximum attenuation and its LO is powered down; RX is on AGC. Every setting in the checklist above has to be written explicitly.
- **`TX LO powerdown = 1` is the classic silent failure.** With the LO off, the DDS or DMA can run and the TX gain can be changed without anything leaving the antenna. The course's own hardware bring-up hit exactly this; [Lab 6.11](/zynq-sdr-course/en/labs/lab-6-11-tx-power-calibration/) restores it to 1 at the end of every run on purpose.
- **An AGC reading of 71 dB is not a measurement setting.** Switch to `manual` before recording anything, or two captures of the same signal will not be comparable.

## Exercises

1. `voltage0` exists as both an input and an output channel of `ad9361-phy`, with different `hardwaregain` values. Check the `iio_attr` help: how do you make a command address only the RX or only the TX channel, and what does the example session above address?
2. Write the minimum sequence of attribute writes that turns this idle state into the RX setting of Lab 6.1 (915 MHz, 2.4 MS/s, 2 MHz, manual gain). Which of them must come before the others?
3. Which attributes must you write, and in which order, to make the TX actually radiate, and which ones must you restore afterwards to return to this safe state?

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
