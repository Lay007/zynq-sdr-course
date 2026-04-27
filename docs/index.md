<div class="hero">

# Zynq SDR Course

**From mathematical model to real RF signal — engineering-grade SDR pipeline**

A complete path:
**Model → DSP → FPGA → RF → Measurement → Analysis**

<div class="hero-actions">
<a class="hero-button" href="model-to-measurement/">Explore pipeline</a>
<a class="hero-button secondary" href="demo/">View IEEE demo</a>
<a class="hero-button secondary" href="ru/">Русская версия</a>
</div>

<div class="badge-line">
<span class="badge-soft">DSP</span>
<span class="badge-soft">FPGA</span>
<span class="badge-soft">RF</span>
<span class="badge-soft">Measurement</span>
<span class="badge-soft">Zynq</span>
</div>

</div>

---

## 🚀 Engineering pipeline

```mermaid
flowchart LR
    MODEL[Model\nMATLAB / Simulink]
    DSP[DSP\nmodulation / filtering]
    FPGA[FPGA\nstream processing]
    RF[RF frontend\nAD9363]
    AIR[Channel\nair / coax]
    RX[Receiver\nRTL-SDR]
    IQ[IQ data\nWAV / RAW]
    ANALYSIS[Analysis\nFFT / EVM / BER]

    MODEL --> DSP --> FPGA --> RF --> AIR --> RX --> IQ --> ANALYSIS
    ANALYSIS -. feedback .-> MODEL
```

---

## 📊 IEEE-style figures

<div class="figure-strip">

<img src="assets/lab01_fft.png" />
<img src="assets/lab03_constellation.png" />
<img src="assets/lab05_evm.png" />
<img src="assets/lab06_ber.png" />

</div>

---

## 🧠 What makes this course different

- Full chain: **theory → hardware → measurement**
- Real RF signal, not simulation-only
- External validation via independent receiver
- IEEE-style reproducible figures

---

## ⚙️ Reproducibility

```bash
bash tools/reproduce_all.sh
```

All figures are generated automatically via CI.
