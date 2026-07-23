# Contents — Block 6. RF Frontend and AD9363

## Theory track
1. RX and TX chain structure
2. levels, gain staging, and dynamic range
3. LO frequencies, bandwidth, and filters
4. AD9363 operating modes
5. noise, overload, and intermodulation
6. ADC resolution, SINAD, SFDR, and system ENOB
7. engineering discipline for RF connections

## Practical track
1. build a level table across the chain
2. experiment with gain and bandwidth
3. identify overload signatures in the spectrum
4. relate AD9363 settings to the observed signal
5. calibrate cable, splitter, and attenuator losses
6. Lab 6.9: compare RTL-SDR and AD936x
7. requantize the AD936x capture to 6/8/10/12 bits
8. extend the test with a strong adjacent blocker and BER/EVM checks

## Review questions
1. Why is nominal 8- or 12-bit resolution different from receiver-system ENOB?
2. What can be isolated by requantizing one capture, and what cannot?
3. Why must gain be manual and the analysis bandwidth common?
4. How do SNR, SINAD, SFDR, EVM, and BER complement one another?
5. Which settings and passive-path losses are required for reproducibility?

## Block outputs
- RF chain level map;
- AD9363 settings description;
- screenshots of overload and normal operation;
- RTL-SDR/AD936x comparison table;
- JSON metrics and SINAD/noise-density figures;
- measurement uncertainty estimate;
- RF-stand report.
