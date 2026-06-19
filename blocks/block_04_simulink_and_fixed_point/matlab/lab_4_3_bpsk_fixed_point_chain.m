% Lab 4.3 - BPSK fixed-point TX/RX chain
%
% MATLAB companion to the Python fixed-point bridge between Block 11 BPSK
% handoff files and the future Simulink/HDL modem route.

clear; close all; clc;

rootDir = fullfile(fileparts(mfilename('fullpath')), '..', '..', '..');
assetDir = fullfile(rootDir, 'docs', 'assets');
packageDir = fullfile(rootDir, 'blocks', 'block_11_integrated_sdr_project', 'assets', 'end_to_end_bpsk_reference');
if ~exist(assetDir, 'dir')
    mkdir(assetDir);
end

required = {
    fullfile(packageDir, 'config.json')
    fullfile(packageDir, 'tx_bits.txt')
    fullfile(packageDir, 'tx_symbols_float.txt')
    fullfile(packageDir, 'tx_symbols_q15.txt')
    fullfile(packageDir, 'rrc_taps_float.txt')
    fullfile(packageDir, 'rrc_taps_q15.txt')
    fullfile(packageDir, 'sample_plan.json')
};

for k = 1:numel(required)
    if exist(required{k}, 'file') ~= 2
        error('Missing required Block 11 handoff file: %s', required{k});
    end
end

cfg = jsondecode(fileread(fullfile(packageDir, 'config.json')));
samplePlan = jsondecode(fileread(fullfile(packageDir, 'sample_plan.json')));
bits = uint8(load(fullfile(packageDir, 'tx_bits.txt')));
symbolPairsFloat = load(fullfile(packageDir, 'tx_symbols_float.txt'));
symbolPairsQ15 = load(fullfile(packageDir, 'tx_symbols_q15.txt'));
tapsFloat = load(fullfile(packageDir, 'rrc_taps_float.txt'));
tapsQ15 = int16(load(fullfile(packageDir, 'rrc_taps_q15.txt')));

txReferenceExport = read_ci16(fullfile(packageDir, sprintf('%s_tx_reference.ci16', cfg.dataset_id)));
capture = read_ci16(fullfile(packageDir, sprintf('%s.ci16', cfg.dataset_id)));

txSymbolsFloat = complex(symbolPairsFloat(:, 1), symbolPairsFloat(:, 2));
txSymbolsQ15 = complex(double(symbolPairsQ15(:, 1)) ./ 32767.0, double(symbolPairsQ15(:, 2)) ./ 32767.0);

upsampledFloat = upsample_complex(txSymbolsFloat, cfg.samples_per_symbol);
txFilterFloat = conv(upsampledFloat, tapsFloat(:));
txGain = cfg.tx_amplitude / max(abs(txFilterFloat));
txGainQ15 = int16(clip(round(txGain * 32767.0), -32768, 32767));
txWaveformFloat = txFilterFloat .* txGain;
txCaptureFloat = [
    complex(zeros(cfg.leading_silence_samples, 1));
    txWaveformFloat;
    complex(zeros(cfg.trailing_silence_samples, 1));
];

[txFilterFixed, txFilterSat] = fixed_point_complex_fir_q15(upsample_complex(txSymbolsQ15, cfg.samples_per_symbol), tapsQ15);
[txWaveformFixed, txGainSat] = fixed_point_real_gain_q15(txFilterFixed, txGainQ15);
txCaptureFixed = [
    complex(zeros(cfg.leading_silence_samples, 1));
    txWaveformFixed;
    complex(zeros(cfg.trailing_silence_samples, 1));
];

txExportRmse = sqrt(mean(abs(txCaptureFloat - txReferenceExport(1:numel(txCaptureFloat))) .^ 2));
txAligned = scalar_align(txWaveformFloat, txWaveformFixed);
txRmsError = sqrt(mean(abs(txWaveformFloat - txAligned) .^ 2));
txEvm = evm_percent(txWaveformFloat, txAligned);

t = (0:numel(capture)-1).' ./ cfg.sample_rate_hz;
rxCorrected = capture .* exp(-1j .* (2.0 .* pi .* cfg.cfo_hz .* t + cfg.phase_offset_rad));
matchedFloat = conv(rxCorrected, tapsFloat(:));
[matchedFixed, rxFilterSat] = fixed_point_complex_fir_q15(rxCorrected, tapsQ15);

sampleStart = samplePlan.matched_filter_sample_start + 1;
sps = cfg.samples_per_symbol;
symbolCount = numel(txSymbolsFloat);
sampleStop = sampleStart + (symbolCount - 1) * sps;
rxSymbolsFloat = matchedFloat(sampleStart:sps:sampleStop);
rxSymbolsFixed = matchedFixed(sampleStart:sps:sampleStop);
rxSymbolsFloatAligned = scalar_align(txSymbolsFloat, rxSymbolsFloat);
rxSymbolsFixedAligned = scalar_align(txSymbolsFloat, rxSymbolsFixed);

preambleCount = numel(cfg.preamble_bits);
[~, berPayloadFloat] = measure_ber(bits, rxSymbolsFloatAligned, preambleCount);
[~, berPayloadFixed] = measure_ber(bits, rxSymbolsFixedAligned, preambleCount);
matchedError = matchedFloat(1:min(numel(matchedFloat), numel(matchedFixed))) - matchedFixed(1:min(numel(matchedFloat), numel(matchedFixed)));

figure('Color', 'w');
shown = min(260, numel(txWaveformFloat));
plot(0:shown-1, real(txWaveformFloat(1:shown)), 'DisplayName', 'float TX real'); hold on;
plot(0:shown-1, real(txAligned(1:shown)), '--', 'DisplayName', 'fixed TX real');
grid on;
xlabel('Sample index'); ylabel('Amplitude');
title('Lab 4.3 - BPSK pulse shaping, float vs fixed');
legend('Location', 'best');
saveas(gcf, fullfile(assetDir, 'lab43_bpsk_fixed_point_tx_waveform_matlab.png'));

figure('Color', 'w');
[freqErr, errDb] = spectrum_db(matchedError, cfg.sample_rate_hz);
plot(freqErr ./ 1e3, errDb);
grid on;
xlabel('Frequency, kHz'); ylabel('Error magnitude, dBFS');
title('Lab 4.3 - Matched-filter float vs fixed error spectrum');
saveas(gcf, fullfile(assetDir, 'lab43_bpsk_fixed_point_error_matlab.png'));

figure('Color', 'w');
shownSymbols = min(240, numel(rxSymbolsFloatAligned));
scatter(real(rxSymbolsFloatAligned(1:shownSymbols)), imag(rxSymbolsFloatAligned(1:shownSymbols)), 12, 'filled', 'DisplayName', 'float RX'); hold on;
scatter(real(rxSymbolsFixedAligned(1:shownSymbols)), imag(rxSymbolsFixedAligned(1:shownSymbols)), 12, 'filled', 'DisplayName', 'fixed RX');
grid on;
xlabel('In-phase'); ylabel('Quadrature');
axis equal;
title('Lab 4.3 - BPSK matched-filter symbol recovery');
legend('Location', 'best');
saveas(gcf, fullfile(assetDir, 'lab43_bpsk_fixed_point_constellation_matlab.png'));

fprintf('Lab 4.3 - BPSK fixed-point chain\n');
fprintf('TX rebuild RMSE vs exported CI16: %.6e\n', txExportRmse);
fprintf('TX fixed RMS error: %.6e\n', txRmsError);
fprintf('TX fixed EVM: %.4f %%\n', txEvm);
fprintf('TX filter/gain saturation count: %d / %d\n', txFilterSat, txGainSat);
fprintf('RX float/fixed payload BER: %.6e / %.6e\n', berPayloadFloat, berPayloadFixed);
fprintf('RX float/fixed EVM: %.4f / %.4f %%\n', evm_percent(txSymbolsFloat, rxSymbolsFloatAligned), evm_percent(txSymbolsFloat, rxSymbolsFixedAligned));
fprintf('RX filter saturation count: %d\n', rxFilterSat);
fprintf('MATLAB figures saved to: %s\n', assetDir);

function x = read_ci16(path)
fid = fopen(path, 'rb');
if fid < 0
    error('Cannot open %s', path);
end
raw = fread(fid, inf, 'int16=>double');
fclose(fid);
if mod(numel(raw), 2) ~= 0
    error('Invalid CI16 file: %s', path);
end
i = raw(1:2:end) ./ 32768.0;
q = raw(2:2:end) ./ 32768.0;
x = complex(i, q);
end

function y = clip(x, lo, hi)
y = min(max(x, lo), hi);
end

function y = upsample_complex(symbols, sps)
y = complex(zeros(numel(symbols) * sps, 1));
y(1:sps:end) = symbols(:);
end

function [y, saturationCount] = fixed_point_complex_fir_q15(x, tapsQ15)
fracBits = 15;
scale = 2^fracBits;
xi = int16(clip(round(real(x) * 32767.0), -32768, 32767));
xq = int16(clip(round(imag(x) * 32767.0), -32768, 32767));
tapsQ15 = int16(tapsQ15(:));
outLen = numel(x) + numel(tapsQ15) - 1;
yi = zeros(outLen, 1, 'int16');
yq = zeros(outLen, 1, 'int16');
saturationCount = 0;

for n = 1:outLen
    accI = int64(0);
    accQ = int64(0);
    kLo = max(1, n - numel(xi) + 1);
    kHi = min(numel(tapsQ15), n);
    for k = kLo:kHi
        idx = n - k + 1;
        coeff = int64(tapsQ15(k));
        accI = accI + int64(xi(idx)) * coeff;
        accQ = accQ + int64(xq(idx)) * coeff;
    end

    ri = bitshift(accI + int64(2^(fracBits-1)), -fracBits);
    rq = bitshift(accQ + int64(2^(fracBits-1)), -fracBits);
    riSat = clip(double(ri), -32768, 32767);
    rqSat = clip(double(rq), -32768, 32767);
    saturationCount = saturationCount + double(riSat ~= double(ri)) + double(rqSat ~= double(rq));
    yi(n) = int16(riSat);
    yq(n) = int16(rqSat);
end

y = (double(yi) + 1j * double(yq)) ./ scale;
end

function [y, saturationCount] = fixed_point_real_gain_q15(x, gainQ15)
fracBits = 15;
scale = 2^fracBits;
xi = int16(clip(round(real(x) * 32767.0), -32768, 32767));
xq = int16(clip(round(imag(x) * 32767.0), -32768, 32767));
yi = zeros(numel(x), 1, 'int16');
yq = zeros(numel(x), 1, 'int16');
saturationCount = 0;

for n = 1:numel(x)
    accI = int64(xi(n)) * int64(gainQ15);
    accQ = int64(xq(n)) * int64(gainQ15);
    ri = bitshift(accI + int64(2^(fracBits-1)), -fracBits);
    rq = bitshift(accQ + int64(2^(fracBits-1)), -fracBits);
    riSat = clip(double(ri), -32768, 32767);
    rqSat = clip(double(rq), -32768, 32767);
    saturationCount = saturationCount + double(riSat ~= double(ri)) + double(rqSat ~= double(rq));
    yi(n) = int16(riSat);
    yq(n) = int16(rqSat);
end

y = (double(yi) + 1j * double(yq)) ./ scale;
end

function aligned = scalar_align(ref, rx)
n = min(numel(ref), numel(rx));
refN = ref(1:n);
rxN = rx(1:n);
gain = (refN' * rxN) / max(refN' * refN, eps);
aligned = rxN ./ gain;
end

function value = evm_percent(ref, rx)
n = min(numel(ref), numel(rx));
refN = ref(1:n);
rxN = rx(1:n);
err = rxN - refN;
refRms = max(sqrt(mean(abs(refN) .^ 2)), eps);
value = 100.0 .* sqrt(mean(abs(err) .^ 2)) ./ refRms;
end

function [berTotal, berPayload] = measure_ber(bits, rxSymbols, payloadOffset)
decisions = uint8(real(rxSymbols(1:numel(bits))) < 0);
errorsTotal = sum(decisions ~= bits);
errorsPayload = sum(decisions(payloadOffset+1:end) ~= bits(payloadOffset+1:end));
berTotal = double(errorsTotal) / max(numel(bits), 1);
berPayload = double(errorsPayload) / max(numel(bits) - payloadOffset, 1);
end

function [freq, magDb] = spectrum_db(x, fs)
n = numel(x);
w = hann(n);
coherentGain = sum(w) / n;
spec = fftshift(fft(x(:) .* w)) ./ (n * coherentGain);
freq = fftshift((-floor(n/2):ceil(n/2)-1).' * fs / n);
magDb = 20 .* log10(max(abs(spec), 1e-15));
end
