# 16. Laboratory Work 5. SDR Impairments: noise, CFO, mismatch and clipping

## Goal
Demonstrate how real-world impairments affect spectrum, constellation, EVM and BER.

The lab covers four typical effects:

- noise;
- carrier frequency offset (CFO);
- I/Q or gain mismatch;
- clipping and overload.

## 1. Learning idea

```text
ideal signal → impairment → reception → metrics → engineering conclusion
```

## 2. Experiment diagram

```mermaid
flowchart TB
    classDef model fill:#E0F2FE,color:#0F172A,stroke:#0284C7;
    classDef impairment fill:#FEF3C7,color:#0F172A,stroke:#D97706;
    classDef rf fill:#FFE4E6,color:#0F172A,stroke:#E11D48;
    classDef metric fill:#F1F5F9,color:#0F172A,stroke:#64748B;

    REF["Reference signal"]:::model
    IMP["Impairment"]:::impairment
    RX["Reception"]:::rf
    SPEC["Spectrum"]:::metric
    CONST["Constellation"]:::metric
    EVM["EVM"]:::metric
    BER["BER"]:::metric

    REF --> IMP --> RX --> SPEC
    RX --> CONST --> EVM
    RX --> BER
```

## 3. Tasks

1. Take a reference IQ signal.
2. Add noise and evaluate SNR.
3. Add CFO and observe constellation rotation.
4. Add gain mismatch.
5. Introduce clipping.
6. Compare FFT, EVM and BER.

## 4. Conclusion

Real SDR systems always contain impairments. The engineering task is to measure and compensate them.
