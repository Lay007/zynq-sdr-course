# 13. Laboratory Work 3. Digital Modulation (BPSK/QPSK)

## Goal
Move from analog modulation to digital modulation and demonstrate how information is represented in the complex plane.

This lab covers:

- **BPSK**;
- **QPSK**.

## 1. Learning idea

```text
bit stream → modulation → IQ signal → RF → reception → synchronization → demodulation → BER
```

This is the first step toward real digital communication systems.

## 2. Experiment diagram

```mermaid
flowchart TB
    classDef dsp fill:#DCFCE7,color:#0F172A,stroke:#16A34A;
    classDef rf fill:#FFE4E6,color:#0F172A,stroke:#E11D48;
    classDef tool fill:#EDE9FE,color:#0F172A,stroke:#7C3AED;

    BITS["1. Bit stream"]:::dsp
    MAP["2. Symbol mapping<br/>BPSK/QPSK"]:::dsp
    SHAPE["3. Pulse shaping<br/>RRC"]:::dsp
    TX["4. RF TX"]:::rf
    CH["5. Channel"]:::rf
    RX["6. RF RX"]:::rf
    DDC["7. Baseband"]:::dsp
    SYNC["8. Synchronization"]:::dsp
    DEMOD["9. Demodulation"]:::dsp
    BER["10. BER estimation"]:::tool

    BITS --> MAP --> SHAPE --> TX --> CH --> RX --> DDC --> SYNC --> DEMOD --> BER
```

## 3. Core concepts

### BPSK
- 1 bit per symbol;
- phase 0 or π;
- robust to noise.

### QPSK
- 2 bits per symbol;
- 4 constellation points;
- higher data rate.

## 4. Tasks

1. Generate a bit stream.
2. Perform modulation (BPSK or QPSK).
3. Transmit the signal.
4. Receive it with RTL-SDR.
5. Perform demodulation.
6. Estimate BER.

## 5. Expected observations

- constellation diagram;
- noise influence;
- synchronization errors;
- BER changes.

## 6. Expected result

The student should:

- understand IQ representation;
- observe constellation;
- evaluate errors;
- connect DSP and RF behavior.

## 7. Engineering conclusion

Digital modulation is the basis of modern communication systems, and SDR allows observing it simultaneously at the model, hardware, and RF levels.
