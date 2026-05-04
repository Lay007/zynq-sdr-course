% Lab 4.1 — Fixed-point FIR filtering
% Generates a synthetic IQ signal, applies float and fixed-point FIR models,
% estimates implementation error and saves IEEE-style figures.

clear; close all; clc;

rootDir = fullfile(fileparts(mfilename('fullpath')), '..', '..', '..');
assetDir = fullfile(rootDir, 'docs', 'assets');
if ~exist(assetDir, 'dir')
    mkdir(assetDir);
end

rng(7);
fs = 2.4e6;
N = 32768;
wantedHz = 120e3;
interfererHz = 620e3;
interfererAmplitude = 0.35;
noiseRms = 0.02;
numTaps = 129;
cutoffHz = 250e3;
fracBits = 15;
scale = 2^fracBits;

t = (0:N-1).' / fs;
x = exp(1j*2*pi*wantedHz*t) + ...
    interfererAmplitude*exp(1j*2*pi*interfererHz*t) + ...
    noiseRms*(randn(N,1) + 1j*randn(N,1));
x = x ./ max(abs(x)) * 0.85;

m = (0:numTaps-1).' - (numTaps-1)/2;
hFloat = 2*cutoffHz/fs * sinc(2*cutoffHz/fs * m);
hFloat = hFloat .* blackman(numTaps);
hFloat = hFloat ./ sum(hFloat);

hQuant = double(clip(round(hFloat * scale), -32768, 32767)) / scale;

yFloat = conv(x, hFloat, 'same');

% Educational Q1.15 fixed-point model using integer arithmetic.
xi = int16(clip(round(real(x) * scale), -32768, 32767));
xq = int16(clip(round(imag(x) * scale), -32768, 32767));
hq = int16(clip(round(hFloat * scale), -32768, 32767));

yi = zeros(N, 1, 'int16');
yq = zeros(N, 1, 'int16');
saturationCount = 0;
half = floor(numTaps/2);

for i = 1:N
    accI = int64(0);
    accQ = int64(0);
    for k = 1:numTaps
        idx = i - k + half + 1;
        if idx >= 1 && idx <= N
            accI = accI + int64(xi(idx)) * int64(hq(k));
            accQ = accQ + int64(xq(idx)) * int64(hq(k));
        end
    end
    ri = round(double(accI) / scale);
    rq = round(double(accQ) / scale);
    riSat = clip(ri, -32768, 32767);
    rqSat = clip(rq, -32768, 32767);
    saturationCount = saturationCount + double(ri ~= riSat) + double(rq ~= rqSat);
    yi(i) = int16(riSat);
    yq(i) = int16(rqSat);
end

yFixed = (double(yi) + 1j*double(yq)) / scale;
err = yFloat - yFixed;
rmsError = sqrt(mean(abs(err).^2));
signalRms = sqrt(mean(abs(yFloat).^2));
sqnrDb = 20*log10(signalRms / max(rmsError, eps));
maxAbsError = max(abs(err));
guardBits = ceil(log2(numTaps));

[fResp, hFloatDb] = responseDb(hFloat, fs);
[~, hQuantDb] = responseDb(hQuant, fs);
figure('Color', 'w');
plot(fResp/1e3, hFloatDb, 'DisplayName', 'float coefficients'); hold on;
plot(fResp/1e3, hQuantDb, 'DisplayName', 'Q1.15 coefficients');
grid on;
xlabel('Frequency, kHz'); ylabel('Magnitude, dB');
title('Lab 4.1 — FIR coefficient quantization');
legend('Location', 'best');
saveas(gcf, fullfile(assetDir, 'lab41_fixed_point_fir_response_matlab.png'));

[f, xDb] = spectrumDb(x, fs);
[~, yFloatDb] = spectrumDb(yFloat, fs);
[~, yFixedDb] = spectrumDb(yFixed, fs);
figure('Color', 'w');
plot(f/1e3, xDb, 'DisplayName', 'input'); hold on;
plot(f/1e3, yFloatDb, 'DisplayName', 'float FIR');
plot(f/1e3, yFixedDb, 'DisplayName', 'fixed FIR');
grid on;
xlabel('Frequency, kHz'); ylabel('Magnitude, dBFS');
title('Lab 4.1 — Fixed-point FIR spectrum comparison');
legend('Location', 'best');
saveas(gcf, fullfile(assetDir, 'lab41_fixed_point_fir_spectrum_matlab.png'));

[fErr, errDb] = spectrumDb(err, fs);
figure('Color', 'w');
plot(fErr/1e3, errDb);
grid on;
xlabel('Frequency, kHz'); ylabel('Error magnitude, dBFS');
title('Lab 4.1 — Fixed-point FIR error spectrum');
saveas(gcf, fullfile(assetDir, 'lab41_fixed_point_fir_error_matlab.png'));

fprintf('Lab 4.1 — Fixed-point FIR\n');
fprintf('FIR taps: %d\n', numTaps);
fprintf('Cutoff: %.1f kHz\n', cutoffHz/1e3);
fprintf('Input/coefficient format: Q1.%d\n', fracBits);
fprintf('Recommended FIR guard bits: %d\n', guardBits);
fprintf('RMS error: %.6e\n', rmsError);
fprintf('Max abs error: %.6e\n', maxAbsError);
fprintf('SQNR: %.2f dB\n', sqnrDb);
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

function [freq, magDb] = responseDb(h, fs)
    nfft = 16384;
    hp = zeros(nfft, 1);
    hp(1:length(h)) = h(:);
    spec = fftshift(fft(hp));
    freq = fftshift((-floor(nfft/2):ceil(nfft/2)-1).' * fs / nfft);
    magDb = 20*log10(max(abs(spec), 1e-15));
end
