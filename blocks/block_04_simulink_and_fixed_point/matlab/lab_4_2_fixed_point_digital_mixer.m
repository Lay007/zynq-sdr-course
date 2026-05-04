% Lab 4.2 — Fixed-point digital mixer
% Generates a complex IQ tone, shifts it with float and Q1.15 fixed-point
% mixers, estimates EVM/spurs and saves IEEE-style figures.

clear; close all; clc;

rootDir = fullfile(fileparts(mfilename('fullpath')), '..', '..', '..');
assetDir = fullfile(rootDir, 'docs', 'assets');
if ~exist(assetDir, 'dir')
    mkdir(assetDir);
end

rng(11);
fs = 2.4e6;
N = 32768;
inputToneHz = 120e3;
shiftHz = -120e3;
noiseRms = 0.01;
fracBits = 15;
phaseBits = 24;
scale = 2^fracBits;

t = (0:N-1).' / fs;
x = exp(1j*2*pi*inputToneHz*t) + noiseRms*(randn(N,1) + 1j*randn(N,1));
x = x ./ max(abs(x)) * 0.80;

phaseIncrement = round(shiftHz / fs * 2^phaseBits);
actualShiftHz = phaseIncrement * fs / 2^phaseBits;
phase = 2*pi*mod((0:N-1).' * phaseIncrement, 2^phaseBits) / 2^phaseBits;
osc = exp(1j*phase);

yFloat = x .* exp(1j*2*pi*shiftHz*t);

xi = int16(clip(round(real(x) * scale), -32768, 32767));
xq = int16(clip(round(imag(x) * scale), -32768, 32767));
ci = int16(clip(round(real(osc) * scale), -32768, 32767));
sq = int16(clip(round(imag(osc) * scale), -32768, 32767));

yi = zeros(N, 1, 'int16');
yq = zeros(N, 1, 'int16');
saturationCount = 0;

for k = 1:N
    accI = int64(xi(k)) * int64(ci(k)) - int64(xq(k)) * int64(sq(k));
    accQ = int64(xi(k)) * int64(sq(k)) + int64(xq(k)) * int64(ci(k));
    ri = round(double(accI) / scale);
    rq = round(double(accQ) / scale);
    riSat = clip(ri, -32768, 32767);
    rqSat = clip(rq, -32768, 32767);
    saturationCount = saturationCount + double(ri ~= riSat) + double(rq ~= rqSat);
    yi(k) = int16(riSat);
    yq(k) = int16(rqSat);
end

yFixed = (double(yi) + 1j*double(yq)) / scale;
err = yFloat - yFixed;
rmsError = sqrt(mean(abs(err).^2));
signalRms = sqrt(mean(abs(yFloat).^2));
evmPct = 100 * rmsError / max(signalRms, eps);
expectedOutputHz = inputToneHz + shiftHz;
measuredPeakHz = estimatePeakFrequency(yFixed, fs);
frequencyShiftErrorHz = measuredPeakHz - expectedOutputHz;
spurDbc = estimateSpurDbc(yFixed);
deltaF = fs / 2^phaseBits;

[f, xDb] = spectrumDb(x, fs);
[~, yFloatDb] = spectrumDb(yFloat, fs);
[~, yFixedDb] = spectrumDb(yFixed, fs);
figure('Color', 'w');
plot(f/1e3, xDb, 'DisplayName', 'input'); hold on;
plot(f/1e3, yFloatDb, 'DisplayName', 'float mixer');
plot(f/1e3, yFixedDb, 'DisplayName', 'fixed mixer');
grid on;
xlabel('Frequency, kHz'); ylabel('Magnitude, dBFS');
title('Lab 4.2 — Fixed-point mixer spectrum comparison');
legend('Location', 'best');
saveas(gcf, fullfile(assetDir, 'lab42_fixed_point_mixer_spectrum_matlab.png'));

[fErr, errDb] = spectrumDb(err, fs);
figure('Color', 'w');
plot(fErr/1e3, errDb);
grid on;
xlabel('Frequency, kHz'); ylabel('Error magnitude, dBFS');
title('Lab 4.2 — Fixed-point mixer error spectrum');
saveas(gcf, fullfile(assetDir, 'lab42_fixed_point_mixer_error_matlab.png'));

bits = [12 16 20 24 28 32];
resolution = fs ./ (2.^bits);
figure('Color', 'w');
semilogy(bits, resolution, '-o');
grid on;
xlabel('Phase accumulator width, bits'); ylabel('Frequency resolution, Hz');
title('Lab 4.2 — NCO frequency resolution');
saveas(gcf, fullfile(assetDir, 'lab42_nco_frequency_resolution_matlab.png'));

fprintf('Lab 4.2 — Fixed-point digital mixer\n');
fprintf('Input tone: %.1f kHz\n', inputToneHz/1e3);
fprintf('Requested shift: %.1f kHz\n', shiftHz/1e3);
fprintf('Actual NCO shift: %.6f kHz\n', actualShiftHz/1e3);
fprintf('Phase bits: %d\n', phaseBits);
fprintf('NCO frequency resolution: %.6f Hz\n', deltaF);
fprintf('Measured output peak: %.3f Hz\n', measuredPeakHz);
fprintf('Frequency shift error: %.3f Hz\n', frequencyShiftErrorHz);
fprintf('RMS error: %.6e\n', rmsError);
fprintf('EVM: %.4f %%\n', evmPct);
fprintf('Largest spur estimate: %.2f dBc\n', spurDbc);
fprintf('Saturation count: %d\n', saturationCount);
fprintf('Figures saved to: %s\n', assetDir);

function y = clip(x, lo, hi)
    y = min(max(x, lo), hi);
end

function [freq, magDb] = spectrumDb(x, fs)
    n = length(x);
    w = hann(n);
    coherentGain = sum(w) / n;
    spec = fftshift(fft(x .* w)) / (n * coherentGain);
    freq = fftshift((-floor(n/2):ceil(n/2)-1).' * fs / n);
    magDb = 20*log10(max(abs(spec), 1e-15));
end

function peakHz = estimatePeakFrequency(x, fs)
    n = length(x);
    w = hann(n);
    spec = fftshift(abs(fft(x .* w)));
    freq = fftshift((-floor(n/2):ceil(n/2)-1).' * fs / n);
    [~, idx] = max(spec);
    peakHz = freq(idx);
end

function spurDbc = estimateSpurDbc(x)
    n = length(x);
    w = hann(n);
    spec = fftshift(abs(fft(x .* w)));
    [peak, peakIdx] = max(spec);
    excludeBins = 6;
    lo = max(1, peakIdx - excludeBins);
    hi = min(n, peakIdx + excludeBins);
    spec(lo:hi) = 0;
    spur = max(spec);
    spurDbc = 20*log10(max(spur, 1e-15) / max(peak, 1e-15));
end
