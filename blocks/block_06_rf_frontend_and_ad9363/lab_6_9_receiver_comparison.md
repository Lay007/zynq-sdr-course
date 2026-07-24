# Lab 6.9 — RTL-SDR vs AD936x receiver quality and ADC resolution

## Goal

Compare an RTL-SDR receiver with a Pluto-compatible Zynq + AD936x receiver under
the same RF stimulus and separate three effects that are often mixed together:

1. the complete receiver-path difference;
2. the influence of output sample resolution;
3. the remaining difference when the AD936x capture is requantized to 8 bits.

The lab does **not** claim that software requantization isolates the physical ADC
perfectly. It provides a controlled estimate that is useful for engineering
comparison and for understanding why nominal ADC bit depth is not the same as
usable system dynamic range.

## Equipment

Recommended conducted setup:

```text
Zynq/AD936x TX
      |
30 dB fixed attenuator
      |
0...31.75 dB step attenuator
      |
2-way 50 ohm splitter
   +--+------------------+
   |                     |
RTL-SDR RX        second Zynq/AD936x RX
```

Required items:

- RTL-SDR with manual tuner gain;
- Zynq-7020 + AD936x board running the Pluto-compatible image;
- a second board or another stable RF source for transmission;
- 50 ohm coaxial cables;
- at least 30 dB of fixed attenuation;
- a two-way splitter/combiner rated for the selected frequency;
- optional digital step attenuator;
- optional NanoVNA for cable/splitter loss characterization;
- optional tinySA for checking transmitter harmonics and unexpected spurs.

Do not connect an enabled transmitter directly to either receiver without a
verified attenuation budget.

## What is being compared

| Comparison | Interpretation |
|---|---|
| RTL-SDR native 8-bit vs AD936x native | Complete receiver difference: RF frontend, LO, filters, gain, ADC, clocking and sample format |
| AD936x native vs the same samples requantized to 8 bits | Quantization-only sensitivity using the same analog capture |
| RTL-SDR 8-bit vs AD936x requantized to 8 bits | Approximate same-resolution path comparison |
| AD936x 6/8/10/12-bit sweep | How the recorded waveform responds to reduced sample resolution |

The third row is still not a pure analog-front-end measurement. Differences in
gain calibration, analog bandwidth, clock phase noise, DC removal and sample-rate
processing remain.

## Metrics

The executable analysis reports:

- tone level in `dBFS`;
- RMS and peak level in `dBFS`;
- DC level;
- SNR in a common analysis bandwidth;
- SINAD;
- SFDR;
- noise density in `dBFS/Hz`;
- system ENOB estimated from SINAD;
- clipping fraction;
- detected tone frequency and frequency error.

The system ENOB is calculated as

```text
ENOB_system = (SINAD - 1.76) / 6.02
```

This is an end-to-end receiver result, not a datasheet characterization of the
standalone ADC.

## Why equal settings matter

Before recording, document and keep fixed:

- RF input power at the splitter input;
- center frequency and tone offset;
- manual receiver gain;
- RF bandwidth;
- sample rate;
- cable and splitter losses;
- capture duration;
- input port;
- AGC state;
- DC/IQ correction state;
- analysis bandwidth.

The two receivers may use different sample rates, but the analysis bandwidth must
be common and must fit inside both Nyquist bands. Never normalize each capture to
its own maximum before calculating `dBFS`, clipping or noise-density metrics.

## Measurement sequence

### 1. Characterize passive losses

Use the NanoVNA or a trusted reference to record:

| Element | Frequency | Insertion loss | Notes |
|---|---:|---:|---|
| fixed attenuator | `____ MHz` | `____ dB` | |
| step attenuator | `____ MHz` | `____ dB` | selected setting |
| splitter path A | `____ MHz` | `____ dB` | RTL-SDR branch |
| splitter path B | `____ MHz` | `____ dB` | AD936x branch |
| cable A | `____ MHz` | `____ dB` | |
| cable B | `____ MHz` | `____ dB` | |

Swap the receiver branches once. If the result changes with the splitter port,
the passive-path asymmetry must be included in the uncertainty budget.

### 2. Configure both receivers

Use manual gain. Choose a tone level that produces approximately `-10...-20 dBFS`
on both receivers without clipping. Record a terminated-input capture for each
receiver before enabling the source.

Suggested starting point:

| Parameter | Value |
|---|---:|
| RF frequency | 915 MHz |
| tone offset | +120 kHz |
| RTL-SDR sample rate | 2.4 MS/s |
| AD936x sample rate | 2.4 or 3.84 MS/s |
| common analysis bandwidth | 1.8 MHz or less |
| capture length | at least 65 536 complex samples |

### 3. Record matched IQ files

Recommended formats:

- RTL-SDR: interleaved unsigned `CU8`;
- AD936x/libiio: interleaved signed `CI16` with 12 significant bits.

Record metadata beside each file. The `CI16` container width is not the ADC
resolution; pass the number of significant bits explicitly to the analyzer.

### 4. Run the offline comparison

Synthetic CI baseline:

```bash
python blocks/block_06_rf_frontend_and_ad9363/python/lab_6_9_compare_receivers.py
```

Real captures:

```bash
python blocks/block_06_rf_frontend_and_ad9363/python/lab_6_9_compare_receivers.py \
  --rtl-iq captures/rtl_915m_tone.cu8 \
  --rtl-format cu8 \
  --rtl-stored-bits 8 \
  --rtl-sample-rate-hz 2400000 \
  --ad936x-iq captures/ad936x_915m_tone.ci16 \
  --ad936x-format ci16 \
  --ad936x-stored-bits 12 \
  --ad936x-sample-rate-hz 3840000 \
  --tone-offset-hz 120000 \
  --tone-search-span-hz 20000 \
  --analysis-bandwidth-hz 1800000 \
  --quantize-bits 6,8,10,12
```

Outputs:

- `docs/assets/lab69_receiver_comparison_metrics.json`;
- `docs/assets/lab69_receiver_comparison_sinad.png`;
- `docs/assets/lab69_receiver_comparison_noise_density.png`.

### 5. Sweep input power

Increase attenuation in 5 or 10 dB steps. At each point record:

| Input level or attenuation | Receiver | Tone dBFS | SNR | SINAD | SFDR | BER/EVM if modulated | Clipping |
|---:|---|---:|---:|---:|---:|---:|---:|
| `____` | RTL-SDR | | | | | | |
| `____` | AD936x native | | | | | | |
| `____` | AD936x -> 8 bit | | | | | | |

For a QPSK extension, add BER and EVM. A receiver can show an apparently good
spectral SNR while BER remains poor because of CFO, impulsive interference,
compression or synchronization failures.

### 6. Strong-blocker extension

Add a strong adjacent carrier while keeping the wanted signal fixed. Increase the
wanted-to-blocker ratio until synchronization or BER fails. This experiment is
usually more informative than a single-tone noise-floor comparison because extra
ADC headroom matters most when a weak wanted signal coexists with a strong
interferer.

## Required conclusions

The report must answer:

1. What is the full native SINAD/SFDR advantage of one receiver over the other?
2. How much does AD936x SINAD degrade when the same samples are reduced to 8 bits?
3. After equalizing resolution at 8 bits, how much difference remains?
4. At what input level does each receiver stop behaving linearly?
5. Does the result follow nominal bit depth, or is it limited by analog noise,
   spurs, gain distribution or clock quality?
6. Are SNR conclusions consistent with BER/EVM for the modulated-signal extension?

## Limitations

Without access to internal analog nodes, this experiment cannot independently
measure the RTL2832U ADC, tuner noise figure and tuner linearity. It measures the
receiver as a system. A calibrated noise source and power meter are required for
a traceable noise-figure measurement. Without them, report practical sensitivity
and uncertainty rather than claiming a calibrated noise figure.
