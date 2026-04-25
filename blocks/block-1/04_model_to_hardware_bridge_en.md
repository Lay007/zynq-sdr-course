# 04. Bridge from Model to Hardware

## Purpose of the section
To understand how a mathematical signal model is connected with real hardware implementation and why the first laboratory work should start from a simple reproducible test signal.

## 1. Why this bridge is needed
In many courses, theory, modeling, and hardware exist separately:
- theory is studied by itself;
- the model lives in MATLAB or Simulink;
- hardware implementation is treated as a separate task.

For engineering training this is not enough.

In a good SDR course the student should see one continuous path:

**model → sample stream → hardware implementation → real signal → external reception → recording → analysis**

This chain is what makes the course practical.

## 2. Why the start should use a simple model
If the course starts with a complex modulation, multi-stage synchronization, and a real protocol, the student quickly loses the connection between causes and the observed result.

That is why the first stage uses the simplest but very useful model:
**generation of a test tone**.

It allows the student to:
- check the whole chain at once;
- remove unnecessary complexity;
- quickly locate errors;
- immediately observe a physical result.

## 3. Why the first signal is a tone
A tone is chosen as the basic educational signal because:
- it is easy to generate;
- it is easy to describe mathematically;
- it is easy to observe in the time domain;
- it is easy to find in the spectrum;
- it is easy to receive with an external receiver;
- it quickly reveals setup errors.

A tone is a useful “checkpoint” for the entire system.

## 4. Signal model in Simulink
At the first stage Simulink is used as an engineering thinking tool.

With it the student can:
- define signal parameters;
- generate an I/Q sequence;
- observe signal behavior;
- evaluate the spectral picture;
- prepare the architecture of the future implementation.

### What the basic model should do
- generate a tone;
- set amplitude;
- set tone frequency;
- operate at the chosen sampling frequency;
- output I and Q;
- show time waveform and spectrum.

## 5. From a real-valued signal to I/Q representation
For future hardware implementation, it is convenient to represent the signal in complex form:
- I channel;
- Q channel.

This matters because real SDR chains usually operate with I/Q streams.

Even if the educational tone is very simple, it is useful to view it from the beginning in a form suitable for a real SDR route.

## 6. Transition from model to digital stream
Once the signal is defined in the model, it can be interpreted as a stream of discrete samples.

At this stage it is important to understand:
- sampling frequency;
- numeric format of samples;
- value range;
- possible quantization;
- future transition to fixed-point.

This is where the student starts to see that the model is not just a “picture”, but already the basis of a digital chain.

## 7. Transition to hardware implementation
Next, the digital stream must be embedded into the hardware system.

In practice this means:
- implementing the generation logic;
- feeding the stream into the chain;
- matching it to the platform architecture;
- connecting it to the RF transceiver.

For a platform based on Zynq7020 + AD9363 this means:
- some functions are placed in FPGA;
- some are configured through the processor system;
- the actual analog signal is formed by the RF chain.

## 8. Why external reception is so important
It would be possible to rely only on internal means of observation, but for an educational course it is important to observe the real signal from the outside.

External reception using RTL-SDR makes it possible to:
- make sure that the signal really exists;
- see it as another receiver sees it;
- obtain independent confirmation of chain operation;
- record the data for offline analysis.

This makes the laboratory work convincing and practically meaningful.

## 9. Full cycle of the first experiment
In the first block the student follows this path:

1. Form the idea of the test signal.
2. Understand the model used to generate it.
3. Relate the model to a digital stream.
4. feed the stream into the hardware implementation.
5. Obtain a real physical signal.
6. Receive it with an external SDR receiver.
7. Observe the spectrum in HDSDR.
8. Save an IQ file.
9. Analyze the recording again in MATLAB, Simulink, Python, C++, and GNU Radio.

## 10. What this approach gives
This approach forms several important skills:

### 1. Connection between mathematics and hardware
The signal exists not only in a formula and not only in a software window.

### 2. Understanding of limitations
Sampling rate, quantization, levels, noise, and parasitic components all appear in a real experiment.

### 3. Ability to verify hypotheses
The student can:
- predict how the spectrum should look;
- check it in the model;
- see it on real reception;
- confirm the result through offline analysis.

## 11. What comes next
In later blocks the same logic will be extended to:
- transition to fixed-point;
- filtering;
- DDC/DUC;
- modulation;
- demodulation;
- hardware implementation of more complex DSP chains;
- circuit-design support around the experiment.

But the foundation is laid here — on a simple but complete route.

## 12. Conclusions
After studying this section, the student should understand:
- why a model is needed before hardware implementation;
- why a test tone is the right starting point;
- how Simulink, the digital stream, and the SDR board are connected;
- why external reception through RTL-SDR is an important part of verification.

## Review questions
1. Why is it important in this course to connect the model and the hardware implementation?
2. Why is it better to use a tone at the first stage?
3. What does I/Q representation give?
4. Why is external reception better than only internal control?
5. Which stages are included in the full cycle of the first experiment?
6. What does the student gain by going from model to real signal?
