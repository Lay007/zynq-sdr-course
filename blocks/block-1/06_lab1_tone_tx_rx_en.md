# 06. Laboratory Work 1. Transmission and Reception of a Test Tone

## Goal of the work
Generate a test tone on the SDR board and receive it with RTL-SDR while visualizing it in HDSDR, then prepare the data for further analysis.

## 1. Tasks of the laboratory work
During the laboratory work the student should:

- prepare the equipment;
- start generation of the test signal;
- configure external reception with RTL-SDR;
- detect the signal in HDSDR;
- evaluate the signal parameters;
- save screenshots;
- record an IQ file;
- prepare materials for further analysis.

## 2. Equipment used
- SDR board based on **Zynq7020 + AD9363**
- **RTL-SDR** receiver
- personal computer
- cables or antennas
- attenuators and adapters if required

## 3. Software used
- HDSDR
- RTL-SDR driver
- MATLAB / Simulink
- Python
- GNU Radio if needed

## 4. Theoretical background
A **test tone** is used in this laboratory work.

A tone is convenient because it:
- is easy to observe in the spectrum;
- produces a distinct narrow peak;
- allows quick verification of frequency tuning;
- is easy to record and analyze again.

If the system works correctly, the student should observe:
- a stable spectral peak;
- stable frequency location;
- a change in level when amplitude changes;
- predictable shift of the peak when the tone frequency changes.

## 5. Workplace preparation
Before starting the work it is necessary to:

1. Connect the SDR board.
2. Connect RTL-SDR to the computer.
3. Check power to the devices.
4. Prepare cables or antennas.
5. Launch HDSDR.
6. Verify that RTL-SDR is recognized by the system.
7. Prepare a folder for:
   - screenshots,
   - IQ files,
   - the report.

## 6. Safety measures
During the lab the following rules must be followed:

- do not connect the transmitting and receiving paths directly without level control;
- do not apply excessive signal level to the RTL-SDR input;
- use attenuators when necessary;
- check connector types and wiring;
- avoid accidental shorts and incorrect power connections.

## 7. Preparing the signal on the SDR board
A configuration that generates a test tone must be started on the SDR board.

### Required parameters
At minimum the following should be defined:
- transmit center frequency;
- tone frequency;
- amplitude;
- signal-output mode.

### What must be documented
The report should include:
- carrier frequency;
- tone frequency;
- chosen link method — over-the-air or cable;
- additional path elements.

## 8. Configuring RTL-SDR and HDSDR
Perform the following actions:

1. Launch HDSDR.
2. Select RTL-SDR as the signal source.
3. Set the receive frequency that matches the experiment.
4. Adjust the observation bandwidth.
5. Choose a reasonable gain level.
6. Observe the noise floor and the expected signal region.

### What counts as a successful result
A stable spectral peak corresponding to the test signal must be detected.

## 9. Signal observation
After the receiver is configured, the student should:

- find the test tone in the spectrum;
- estimate how stable the level is;
- verify the frequency position of the signal;
- observe the signal on the waterfall;
- make sure the observation is repeatable.

### Special attention should be paid to:
- presence of one main peak;
- possible parasitic components;
- how the spectrum changes when generator parameters are changed;
- signs of receiver overload.

## 10. Changing signal parameters
After successfully observing the basic variant, the experiment parameters should be changed.

### Recommended actions
1. Change the tone frequency.
2. Change the amplitude.
3. If possible, change the carrier frequency.
4. Compare the spectral peak position and level before and after the changes.

### What should be documented
- how the peak position changed;
- how the level changed;
- whether the signal remained stable;
- whether additional artifacts appeared.

## 11. Recording an IQ file
After stable reception is achieved, record IQ data.

### Purpose of the recording
The recording is needed for later analysis in:
- MATLAB;
- Simulink;
- Python;
- C++;
- GNU Radio.

### What should be saved together with the recording
- receive frequency;
- sampling rate;
- recording format;
- date and time of the experiment;
- generator parameters;
- comments about experimental conditions.

## 12. What the report should include
The report should contain:

### 1. Goal of the work
A short description of the task of the laboratory work.

### 2. Setup composition
List of equipment and software.

### 3. Experiment parameters
- transmit frequency;
- tone frequency;
- connection method;
- receive parameters;
- additional path elements.

### 4. Observation results
- screenshot of the spectrum;
- screenshot of the waterfall;
- description of signal position;
- description of signal stability.

### 5. Parameter variation
- what was changed;
- how it appeared in the spectrum.

### 6. IQ recording
- file name;
- data format;
- recording conditions.

### 7. Conclusions
A short engineering conclusion about the experiment.

## 13. Expected results
After completing the laboratory work the student should obtain:
- a detected test signal;
- spectral confirmation that the chain works;
- an IQ recording;
- a set of screenshots for the report;
- understanding of the connection between signal generation and observation by an external receiver.

## 14. Typical problems
### Signal is not detected
Possible reasons:
- wrong receive frequency;
- generation is not started;
- incorrect wiring;
- signal level is too low;
- configuration error in the chain.

### Signal is too weak
Possible reasons:
- poor connection;
- insufficient gain;
- too large a distance;
- path losses.

### Signal overloads the receiver
Signs:
- distorted spectrum;
- multiple parasitic peaks;
- unstable level;
- a “dirty” or saturated spectrum.

### Signal instability
Possible reasons:
- poor contacts;
- unstable power;
- external interference;
- incorrect generator settings.

## 15. Review questions
1. Why is a tone chosen for the first laboratory work?
2. What should the student observe in the spectrum?
3. How does an amplitude change affect the observed signal?
4. How does changing tone frequency affect the spectral picture?
5. Why is recording an IQ file needed?
6. Why is it important to document the experiment parameters?
7. Which signs may indicate receiver overload?

## 16. Conclusions
The first laboratory work is fundamental for the whole course.

It shows the student the full minimal cycle of an SDR experiment:

**generation → transmission → reception → observation → recording**

In the next blocks, this cycle will be expanded with:
- more complex signals;
- Simulink modeling;
- transition to fixed-point;
- FPGA implementation;
- circuit-design support around the experiment.
