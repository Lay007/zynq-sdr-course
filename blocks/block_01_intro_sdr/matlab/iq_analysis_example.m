filename = 'tone_capture_iq.bin';
fs = 2.4e6;
dtype = 'int16';

fid = fopen(filename, 'rb');
if fid < 0
    error('Cannot open file: %s', filename);
end

raw = fread(fid, dtype);
fclose(fid);

if mod(numel(raw), 2) ~= 0
    error('IQ file length is not even');
end

i_data = raw(1:2:end);
q_data = raw(2:2:end);
x = double(i_data) + 1j * double(q_data);

n_view = min(length(x), 2000);
t = (0:n_view-1) / fs;

figure;
plot(t, real(x(1:n_view)));
xlabel('Time, s');
ylabel('Amplitude');
title('Real part of IQ signal');
grid on;

nfft = min(length(x), 4096);
X = fftshift(fft(x(1:nfft), nfft));
f = (-nfft/2:nfft/2-1) * (fs / nfft);

figure;
plot(f, 20*log10(abs(X) + 1e-12));
xlabel('Frequency, Hz');
ylabel('Magnitude, dB');
title('Spectrum of recorded tone');
grid on;
