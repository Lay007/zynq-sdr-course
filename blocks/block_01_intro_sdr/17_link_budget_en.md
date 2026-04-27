# 17. Link Budget in SDR Systems

## Goal
Estimate whether a transmitted signal can be successfully received.

## 1. Basic equation

```text
Prx = Ptx + Gtx + Grx - Losses
```

Where:

- `Ptx` — transmit power;
- `Gtx` — transmit gain;
- `Grx` — receive gain;
- `Losses` — path and cable losses.

## 2. Components of the link

### Transmitter
- output power;
- RF frontend characteristics.

### Channel
- cable loss;
- free-space path loss;
- attenuation;
- reflections.

### Receiver
- antenna gain;
- LNA gain;
- SDR gain settings.

## 3. Practical SDR considerations

- RTL-SDR has limited dynamic range;
- too much gain leads to clipping;
- too little gain leads to poor SNR;
- near-field setups behave differently from far-field links.

## 4. Diagram

```mermaid
flowchart TB
    classDef rf fill:#FFE4E6,color:#0F172A,stroke:#E11D48;
    classDef metric fill:#F1F5F9,color:#0F172A,stroke:#64748B;

    TX["Transmitter"]:::rf
    CH["Channel / losses"]:::rf
    RX["Receiver"]:::rf
    P["Received power"]:::metric

    TX --> CH --> RX --> P
```

## 5. Engineering conclusion

Link budget allows predicting whether a signal will be visible before performing the experiment.
