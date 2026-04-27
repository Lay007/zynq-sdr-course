# 12. Laboratory Work 2. AM/FM Modulation and Demodulation

## Goal
Move from a single test tone to simple modulated signals and show how the SDR stand can be used to observe waveform behavior, spectrum, IQ recording, and offline demodulation.

This laboratory work is based on two fundamental modulation types:

- **AM** — amplitude modulation;
- **FM** — frequency modulation.

The goal is not only to see a signal in the spectrum, but also to connect the mathematical model, modulation parameters, RF observation, and offline analysis.

## 1. Learning idea
After Laboratory Work 1, the student already knows how to generate and receive a simple tone. In this lab, the same stand is used for a more meaningful communication experiment:

```text
message → modulator → RF transmission → RTL-SDR/HDSDR → IQ recording → demodulator → comparison with the original message
```

This is the first step from basic chain verification to real analog and digital communication.

## 2. Hardware and software
The same stand is used:

- **Zynq7020 + AD9363** SDR board;
- **RTL-SDR** receiver;
- PC;
- HDSDR;
- MATLAB / Simulink;
- Python;
- GNU Radio;
- cable or over-the-air connection;
- attenuators if required.

## 3. Experiment diagram

```mermaid
flowchart TB
    classDef model fill:#E0F2FE,color:#0F172A,stroke:#0284C7,stroke-width:1px;
    classDef dsp fill:#DCFCE7,color:#0F172A,stroke:#16A34A,stroke-width:1px;
    classDef rf fill:#FFE4E6,color:#0F172A,stroke:#E11D48,stroke-width:1px;
    classDef tool fill:#EDE9FE,color:#0F172A,stroke:#7C3AED,stroke-width:1px;
    classDef result fill:#F1F5F9,color:#0F172A,stroke:#64748B,stroke-width:1px;

    MSG["1. Message signal<br/>tone / audio / test sequence"]:::model
    SELECT["2. Modulation mode<br/>AM or FM"]:::model
    MOD["3. SDR modulator<br/>envelope or frequency deviation"]:::dsp
    TX["4. AD9363 TX path<br/>RF output"]:::rf
    LINK["5. RF link<br/>coax / attenuator / antenna"]:::rf
    RX["6. RTL-SDR reception<br/>gain and frequency setup"]:::tool
    VIEW["7. HDSDR observation<br/>spectrum / waterfall"]:::tool
    IQ["8. IQ recording<br/>dataset for replay"]:::tool
    DEMOD["9. Offline demodulation<br/>AM envelope / FM discriminator"]:::dsp
    COMPARE["10. Comparison<br/>message recovery / distortion / SNR"]:::result
    REPORT["11. Lab report<br/>plots / screenshots / conclusions"]:::result

    MSG --> SELECT --> MOD --> TX --> LINK --> RX --> VIEW --> IQ --> DEMOD --> COMPARE --> REPORT
    COMPARE -. parameter tuning .-> MOD
    COMPARE -. receiver gain tuning .-> RX
```

## 4. Experiment parameters
The report must document:

| Parameter | Meaning |
|---|---|
| `Fc` | transmit carrier frequency |
| `Fs` | IQ sampling rate |
| `Fm` | message-signal frequency |
| `m` | AM modulation index |
| `Δf` | FM frequency deviation |
| `gain_tx` | transmitter gain |
| `gain_rx` | RTL-SDR gain |
| `format` | IQ recording format |

## 5. Part A — AM modulation
### Tasks
1. Generate a low-frequency message signal.
2. Generate an AM signal on the SDR board or in the reference model.
3. Transmit the signal through the RF path.
4. Receive the signal with RTL-SDR.
5. Observe the carrier and sidebands in the spectrum.
6. Record an IQ file.
7. Perform offline envelope demodulation.
8. Compare the recovered message with the original message.

### Expected observations
For AM, the student should observe:

- the central carrier;
- two sidebands;
- spectral changes when the message frequency changes;
- sideband-level changes when the modulation index changes.

## 6. Part B — FM modulation
### Tasks
1. Generate a low-frequency message signal.
2. Configure the frequency deviation.
3. Generate an FM signal.
4. Receive it with RTL-SDR.
5. Observe spectrum broadening.
6. Record IQ data.
7. Perform offline FM demodulation.
8. Compare the recovered message with the original message.

### Expected observations
For FM, the student should observe:

- occupied bandwidth changes when deviation changes;
- the difference between FM and AM spectra;
- sensitivity to receive-frequency tuning;
- the influence of gain and overload on demodulation quality.

## 7. Offline analysis
For each mode, build:

- time-domain waveform of IQ or recovered message;
- received-signal spectrum;
- demodulated-message spectrum;
- comparison of original and recovered message;
- short distortion estimate.

## 8. Review questions
1. How does AM differ from FM in the spectrum?
2. Why do AM sidebands appear?
3. What is modulation index?
4. What is FM frequency deviation?
5. Why does FM usually occupy a wider bandwidth?
6. What happens when RTL-SDR is overloaded?
7. Why must IQ recordings be saved together with experiment parameters?

## 9. Expected result
After completing this lab, the student should obtain:

- IQ recordings of AM and FM signals;
- HDSDR screenshots;
- spectrum plots;
- recovered messages after demodulation;
- understanding of the link between modulation parameters and observed spectrum.

## 10. Engineering conclusion
This laboratory work turns the stand from a simple tone generator into a basic SDR measurement system. The student starts to see modulation not as an abstract formula, but as a measurable change in waveform, spectrum, and occupied bandwidth.
