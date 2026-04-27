# Model → FPGA → RF → Measurement

This page is the **core of the course**. It describes how a signal travels from a mathematical idea to a real RF waveform and back to data.

---

## End-to-end system view

```mermaid
flowchart TB
    MODEL["1. Reference model<br/>MATLAB / Simulink, ideal floating-point behavior and expected spectrum"]
    FIXED["2. Fixed-point model<br/>word length, scaling, overflow margins and quantization noise"]
    FPGA["3. FPGA pipeline<br/>DDS, mixer, FIR, interpolation, AXI-Stream and latency"]
    RF["4. RF transmit path<br/>AD9363 DAC, mixer, filters, gain and frequency plan"]
    CHANNEL["5. Physical channel<br/>coax with attenuation or controlled over-the-air path"]
    RX["6. Independent receiver<br/>RTL-SDR / HDSDR observation outside the main board"]
    IQ["7. IQ recording<br/>WAV / RAW / CI16 data with sample-rate and frequency metadata"]
    ANALYSIS["8. Offline analysis<br/>FFT, EVM, BER, SNR, spurs and repeatability checks"]
    DECISION["9. Engineering decision<br/>accept, retune, redesign or repeat the experiment"]

    MODEL --> FIXED --> FPGA --> RF --> CHANNEL --> RX --> IQ --> ANALYSIS --> DECISION
    DECISION -. algorithm redesign .-> MODEL
    DECISION -. numeric scaling fix .-> FIXED
    DECISION -. RF gain retuning .-> RF
```

---

## Engineering interpretation

| Stage | Key risk | What you verify |
|---|---|---|
| Model | wrong assumptions | spectrum, waveform |
| Fixed-point | quantization | SNR degradation |
| FPGA | architecture | real-time capability |
| RF | analog effects | distortions, gain |
| Receiver | measurement errors | independent observation |
| Analysis | wrong metrics | false conclusions |

---

## FPGA signal path

```mermaid
flowchart TB
    IN["1. Input sample stream<br/>test vector, DMA stream or internally generated waveform"]
    DDS["2. DDS / NCO<br/>phase accumulator, LUT/CORDIC and frequency word"]
    MIX["3. Digital mixer<br/>complex multiplication and frequency translation"]
    FIR["4. FIR filter<br/>pulse shaping, low-pass filtering or image rejection"]
    RATE["5. Rate adaptation<br/>interpolation / decimation for the RF frontend rate"]
    AXI["6. AXI-Stream output<br/>valid/ready timing, framing and backpressure"]
    OUT["7. AD9363 interface<br/>samples delivered to the RF transmit path"]

    IN --> DDS --> MIX --> FIR --> RATE --> AXI --> OUT
```

---

## SDR TX/RX chain

```mermaid
flowchart TB
    SRC["1. Source and framing<br/>tone, packet, payload or waveform definition"]
    MOD["2. Modulation and shaping<br/>BPSK/QPSK/QAM/FSK plus pulse-shaping filters"]
    TXRF["3. TX path<br/>DUC, DAC, mixer, filters and transmit gain"]
    CH["4. Channel<br/>coax, attenuator, antenna path, noise and offsets"]
    RXRF["5. RX path<br/>LNA, mixer, ADC, DDC and AGC"]
    SYNC["6. Synchronization and demodulation<br/>CFO, timing, frame sync, matched filter and bits"]
    VALID["7. Validation and replay<br/>IQ taps, FFT, EVM, BER, reports and notebooks"]

    SRC --> MOD --> TXRF --> CH --> RXRF --> SYNC --> VALID
    VALID -. model tuning .-> MOD
    VALID -. hardware tuning .-> RXRF
```

---

## Measurement loop

```mermaid
flowchart LR
    TX["Zynq TX<br/>configured waveform"]
    AIR["RF path<br/>safe level"]
    RTL["RTL-SDR<br/>external RX"]
    HDSDR["HDSDR<br/>observe"]
    FILE["IQ file<br/>record"]
    MATLAB["MATLAB / Python<br/>analyze"]

    TX --> AIR --> RTL --> HDSDR --> FILE --> MATLAB
    MATLAB -. feedback .-> TX
```

---

## Key takeaway

```text
Model → Hardware → Measurement → Decision
```

If any stage is skipped, the engineering result is unreliable.
