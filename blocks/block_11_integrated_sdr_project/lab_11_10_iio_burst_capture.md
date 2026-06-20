# Lab 11.10 - Timed IIO RX snapshot around the discovery burst

## Goal

Confirm whether the AD9361 receive stream shows any energy event around the gpreg-triggered BPSK discovery burst, even before the BER chain reports non-zero `RECEIVED_BITS`.

## Engineering question

> If the gpreg control plane finishes but `RECEIVED_BITS` stays at zero, does the host-side IIO stream still show a timed RF/IF event around the burst trigger?

## Script

| File | Purpose |
|---|---|
| `blocks/block_11_integrated_sdr_project/python/lab_11_10_iio_burst_capture.py` | starts a short `iio_readdev` capture, triggers one gpreg burst over SSH/devmem, and writes a JSON report with capture-power metrics |

## Why this step matters

The RF discovery sweep already showed that the control plane is alive, but it did not answer a narrower question:

- is any burst-shaped energy visible on the AD9361 RX DMA stream;
- does that event occur near the intended trigger time;
- is the remaining problem mostly RF visibility, or already inside the matched-filter / BER path.

That distinction changes the next debugging step.

## Example run

```bash
python blocks/block_11_integrated_sdr_project/python/lab_11_10_iio_burst_capture.py \
  --ssh-host 192.168.40.1 \
  --ssh-user root \
  --ssh-password analog \
  --iio-uri ip:192.168.40.1 \
  --sample-count 2097152 \
  --trigger-delay-ms 10 \
  --json-out docs/assets/lab110_iio_burst_capture_live.json
```

## Report contract

The JSON report should capture:

- AD9361 state before the timed capture;
- AD9361 state after optional RF configuration and after restore;
- `iio_readdev` byte count and optional CI16 output path;
- the gpreg burst result and register snapshot;
- windowed power metrics relative to the expected trigger time.

## Interpretation

Three outcomes are especially useful:

1. `energy_event_detected = true` and the event is close to the trigger time.
2. `energy_event_detected = true` but far from the trigger time.
3. `energy_event_detected = false` and the capture looks like stationary noise only.

The first case points toward digital receive-chain alignment. The third case points back toward RF visibility, TX enable, or path coupling.

## Engineering conclusion template

```text
The timed capture recorded ______ complex samples at ______ MS/s.
The strongest power window occurred ______ ms from the expected trigger.
The burst helper reported RECEIVED_BITS = ______.
The next step is ______.
```
