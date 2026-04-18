clear; close all; clc;
Fs  = 1.0e6;
N   = 4096;
f0  = 100e3;
A   = 0.9;
phi = pi/6;
n = 0:N-1;
t = n / Fs;
x = A * exp(1j * (2*pi*f0/Fs*n + phi));
I = real(x); Q = imag(x);
X = fftshift(fft(x));
f = (-N/2:N/2-1) * (Fs/N);
magX = 20*log10(abs(X) + 1e-12);
out_dir = "results"; if ~exist(out_dir, 'dir'); mkdir(out_dir); end
writematrix([I(:), Q(:)], fullfile(out_dir, "iq_tone_basic_iq.txt"), "Delimiter", "space");
figure; plot(t(1:200)*1e6, I(1:200)); hold on; plot(t(1:200)*1e6, Q(1:200)); grid on; title('I and Q');
figure; plot(I(1:400), Q(1:400), '.'); grid on; axis equal; title('IQ');
figure; plot(f/1e3, magX); grid on; title('FFT');
