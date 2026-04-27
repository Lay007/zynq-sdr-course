# Measurement Errors and Pitfalls

This page summarizes real-world SDR mistakes.

---

## Receiver overload

Symptom:
- flat-topped waveform
- distorted FFT

Fix:
- reduce gain
- add attenuation

---

## DC offset

Symptom:
- spike at zero frequency

Fix:
- enable DC removal

---

## Aliasing

Symptom:
- mirrored spectrum

Fix:
- correct sampling rate

---

## CFO (Carrier Frequency Offset)

Symptom:
- rotating constellation

Fix:
- frequency correction

---

## Clipping

Symptom:
- distorted constellation

Fix:
- gain control

---

## Engineering takeaway

Every SDR measurement must be treated critically.
