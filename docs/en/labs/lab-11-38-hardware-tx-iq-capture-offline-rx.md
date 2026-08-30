# Lab 11.38 — ZynqSDR TX → IQ capture → offline receiver

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

### Executable Python baseline

The first deterministic receiver is implemented in:

```text
blocks/block_11_integrated_sdr_project/python/lab_11_38_offline_qpsk_rx.py
```

Run its no-hardware self-test first:

```bash
python blocks/block_11_integrated_sdr_project/python/lab_11_38_offline_qpsk_rx.py --self-test
```

The self-test deliberately puts one known course frame inside a longer recording, then adds an unknown sample offset, carrier phase, CFO, DC offset and AWGN. A PASS proves that the **offline algorithm** can acquire and decode that reference recording. It does not prove a ZynqSDR or RTL-SDR hardware reception.

For a real ZynqSDR `ci16` recording:

```bash
python blocks/block_11_integrated_sdr_project/python/lab_11_38_offline_qpsk_rx.py \
  measurements/qpsk_hw_tx_capture_001.ci16 \
  --output measurements/qpsk_hw_tx_capture_001_rx.json
```

The matching metadata file is automatically taken from:

```text
measurements/qpsk_hw_tx_capture_001.json
```

The same command works for an RTL-SDR `.cu8` capture when the sidecar declares `"iq_format": "cu8"`. The receiver uses the **actual** `sampling.sample_rate_hz` from the sidecar. For example, a 2.4 MS/s RTL-SDR recording is converted explicitly to the 3.84 MS/s course-model rate with the rational ratio `8/5`; the code does not silently pretend that the two clocks are equal.

The current Python baseline performs these executable stages:

```text
raw ci16/cu8/cf32 + JSON metadata
  ↓
explicit numeric format conversion
  ↓
DC removal + RMS normalization
  ↓
rational sample-rate conversion, if required
  ↓
committed 65-tap course RRC matched filter
  ↓
scan all 8 integer sample phases
  ↓
4th-power QPSK coarse CFO acquisition
  ↓
normalized preamble correlation / automatic frame start
  ↓
residual carrier phase/CFO fit on the preamble
  ↓
QPSK hard decisions
  ↓
BER + EVM + CFO + sync metric JSON
```

For the 480 kSym/s QPSK baseline, the fourth-power coarse estimator has an unambiguous acquisition interval of approximately ±60 kHz. A real RTL-SDR capture outside that interval needs better RF tuning or a future wider-range coarse-CFO stage; do not hide that limitation by manually rotating the final constellation.

The current v1 receiver decodes the committed **140-symbol / 280-bit known course frame**. The Lab 11.46 packet-v1 codec and digital loopback now exist, but packet parsing, sequence extraction and CRC are not yet integrated into this offline receiver and are intentionally not claimed here.

## Stage 4 — reference RX pipeline and diagnostics

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

The companion diagnostic tool reuses the exact same receiver functions:

```text
blocks/block_11_integrated_sdr_project/python/offline_qpsk_diagnostics.py
```

First verify it on the synthetic/reference recording:

```bash
python blocks/block_11_integrated_sdr_project/python/offline_qpsk_diagnostics.py \
  --self-test \
  --plot-dir measurements/lab1138_selftest_plots
```

For a real capture:

```bash
python blocks/block_11_integrated_sdr_project/python/offline_qpsk_diagnostics.py \
  measurements/qpsk_hw_tx_capture_001.ci16 \
  --plot-dir measurements/qpsk_hw_tx_capture_001_plots
```

It writes five independent PNG artifacts:

```text
spectrum.png
sync-metric.png
constellation-before-carrier-correction.png
constellation-after-carrier-correction.png
matched-filter-timing.png
```

The plotter deliberately calls the same format adapter, rational resampler, RRC, CFO estimator and frame-acquisition code as the numeric receiver. The plots therefore expose the receiver rather than forming a second, easier analysis path. CI checks that all five PNGs are generated from an uncropped synthetic/reference capture.

## Stage 5 — message decoding

Use the Lab 11.46 application packet for the next integration step:

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

A CI/self-test PASS of `lab_11_38_offline_qpsk_rx.py` and its diagnostic plotter satisfies only the software/reference part of items 3–6. The lab itself remains hardware-pending until a real capture is processed successfully.

## Next step

After this lab passes, continue to Lab 11.45 (differential QPSK and a longer preamble), then to [Lab 11.46 — a message from one Zynq console to another](lab-11-46-two-board-console-message.md), gradually replacing the offline reference receiver with second-board hardware blocks.
