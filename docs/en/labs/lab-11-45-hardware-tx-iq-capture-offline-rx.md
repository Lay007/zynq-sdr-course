# Lab 11.45 — ZynqSDR TX → IQ capture → offline receiver

## Idea

Before moving the complete RX chain into the PL of a second board, split the problem into two observable parts:

```text
ZynqSDR A
PS / packet source
      ↓
PL: existing QPSK TX
      ↓
AD936x TX
      ↓ RF / cable
      ↓
┌───────────────────────────────┐
│ option A: ZynqSDR B + AD936x  │
│ option B: RTL-SDR             │
└───────────────────────────────┘
      ↓
raw IQ capture + metadata
      ↓
MATLAB / Python reference RX
      ↓
CFO → matched filter → timing → carrier recovery
      ↓
frame sync → QPSK demap → packet decode → CRC
      ↓
"Hello from board A"
```

The transmitter is already real hardware. Reception stays fully observable: every DSP stage can be plotted, compared with a reference and replayed against the same saved IQ file.

## Why this stage comes before a real-time PL RX

If hardware TX and hardware RX are introduced at the same time, a failure can come from many places: TX, RF path, CFO, sample-rate mismatch, matched filtering, timing recovery, carrier recovery, frame sync, or packet framing.

A saved IQ recording creates a clean boundary:

```text
hardware TX + RF + ADC   |   deterministic offline RX
```

The same capture can then be processed repeatedly by MATLAB/Python, a fixed-point model, and later RTL replay. It becomes a practical golden reference for the future PL receiver.

## Two receiver options

### Option A — second ZynqSDR

```text
AD936x RX → IIO capture → .ci16 + .json
```

Advantages:

- receiver architecture is close to the future second-board design;
- more IQ resolution;
- easy comparison with the eventual real-time Zynq RX;
- capture sample rate can be selected for the reference model.

### Option B — RTL-SDR

```text
RTL-SDR → rtl_sdr / compatible recorder → .cu8 + .json
```

Advantages:

- inexpensive independent observer;
- strong evidence that the waveform really exists at RF;
- exposes useful real limitations: 8-bit IQ, DC spur, oscillator ppm/CFO and a different sample rate.

Do not force the RTL-SDR capture rate to equal the TX sample rate. Store the **actual capture sample rate** in metadata and let the offline model perform rational resampling when required.

## Recording contract

Reuse the existing [IQ recording metadata guide](../../iq-recording-metadata.md).

Every capture contains at least two files:

```text
qpsk_hw_tx_capture_001.ci16   # ZynqSDR RX
qpsk_hw_tx_capture_001.json
```

or

```text
qpsk_hw_tx_capture_001.cu8    # RTL-SDR RX
qpsk_hw_tx_capture_001.json
```

The metadata must include:

- TX board/build identity;
- RX device;
- center frequency;
- RX sample rate;
- gain mode and gain;
- RF bandwidth;
- attenuation / cable path;
- IQ format;
- sample count;
- transmitted packet sequence;
- expected payload or PRBS seed.

An IQ file without matching metadata is not considered reproducible lab evidence.

## Stage 1 — hardware transmitter

Reuse the existing course QPSK TX datapath. Do not create a new PHY for this lab.

For the first PASS, transmit a repeated fixed frame with a known payload. Once the packet bridge exists, reuse the same fixed 32-byte packet format as Lab 11.46.

Before recording, verify TX center frequency, sample rate, TX gain, safe conducted attenuation and the absence of RX overload.

## Stage 2 — IQ recording

Record a segment long enough to contain several frames plus idle samples before and after them.

Do not manually crop the capture to a perfect packet. The offline receiver should find the frame inside a longer recording.

For RTL-SDR, record the actual `sample_rate_hz`; it may differ from both the TX rate and the internal model rate.

## Stage 3 — input normalization

The offline model begins with an explicit format adapter:

```text
.cu8 / .ci16
      ↓
complex floating-point reference samples
      ↓
DC removal / normalization
      ↓
optional rational resampler
```

Do not hide this conversion inside later DSP. The learner should see that `cu8`, `ci16`, and model complex samples are different numerical representations of the same waveform.

## Stage 4 — reference RX pipeline

Recommended order:

```text
1. spectrum / waterfall sanity check
2. coarse CFO estimate
3. CFO correction
4. RRC matched filter
5. timing recovery
6. residual carrier / phase recovery
7. frame synchronization
8. QPSK decisions
9. payload recovery
10. CRC / BER / EVM metrics
```

Keep at least one diagnostic result from every important stage rather than only the final BER.

Useful minimum plots include spectrum before correction, constellation before/after carrier correction, matched-filter output, timing result, recovered constellation, and packet/frame-sync metric.

## Stage 5 — message decoding

Once the packet bridge exists, reuse the Lab 11.46 application packet:

```text
byte 0      : payload length
bytes 1..2  : sequence
bytes 3..29 : application bytes
bytes 30..31: CRC-16/CCITT
```

Then the acceptance result becomes application-visible:

```text
capture: qpsk_hw_tx_capture_017.cu8
sequence: 17
crc: OK
payload: "Hello from board A"
```

Before the packet bridge is available, a known PRBS or fixed payload with BER comparison is acceptable.

## Stage 6 — compare the two RX devices

If both ZynqSDR B and RTL-SDR are available, record the same TX waveform with both receivers under conditions that are as similar as practical.

Compare:

| Metric | ZynqSDR RX | RTL-SDR RX |
|---|---:|---:|
| sample rate | measured | measured |
| estimated CFO | | |
| EVM after sync | | |
| decoded frames | | |
| CRC OK | | |
| BER/PER | | |

This naturally connects the lab to the existing receiver-comparison material in Block 6.

## The important educational transition

After successful offline decoding, the hardware RX is not built from scratch. Move one block at a time:

```text
captured IQ
  ↓
MATLAB/Python float RX        ← golden reference
  ↓
fixed-point RX
  ↓
RTL block replay on same IQ
  ↓
PL streaming RX
  ↓
real-time two-board RX
```

For every migrated block, keep the same input capture where possible and compare outputs sample-by-sample or metric-by-metric.

## PASS criterion

Minimum hardware/offline PASS:

1. the waveform is physically generated by ZynqSDR TX;
2. IQ is recorded by an independent RX device;
3. the capture has a valid metadata sidecar;
4. the reference model finds and synchronizes the frame by itself;
5. payload/PRBS is recovered;
6. CFO and at least one quality metric (`EVM`, `BER`, or `CRC`) are saved;
7. the result can be reproduced without making a new RF recording.

This is **hardware TX + real RF/IQ capture + offline model evidence**. It is not yet evidence of a real-time PL receiver.

## Next step

After this lab passes, continue to [Lab 11.46 — a message from one Zynq console to another](lab-11-46-two-board-console-message.md), gradually replacing the offline reference receiver with second-board hardware blocks.
