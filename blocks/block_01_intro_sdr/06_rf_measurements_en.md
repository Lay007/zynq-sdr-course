# 06. RF Measurements in SDR

## Goal
Understand real RF limitations: signal level, noise, and overload.

## Key concepts

### Signal level
- too low → buried in noise;
- optimal → good SNR;
- too high → overload.

### Noise
- limits sensitivity;
- affects BER.

### Overload
Signs:
- distorted spectrum;
- harmonics;
- unstable level;
- signal distortion.

## Diagram

```mermaid
flowchart TB
    classDef rf fill:#FFE4E6,color:#0F172A,stroke:#E11D48;
    classDef metric fill:#F1F5F9,color:#0F172A,stroke:#64748B;

    SIG["RF signal"]:::rf
    GAIN["Gain control"]:::rf
    RX["RTL-SDR"]:::rf
    FFT["Spectrum"]:::metric

    SIG --> GAIN --> RX --> FFT
```

## Conclusion

RF limitations affect signal quality as much as DSP.
