# 07. Анализ записанного сигнала в MATLAB

## Цель раздела
Научиться загружать записанный IQ-файл в MATLAB, строить временные и спектральные представления сигнала и оценивать основные параметры тестового тона.

## Основные задачи
1. Загрузить IQ-файл.
2. Преобразовать его в комплексный сигнал.
3. Построить фрагмент временной реализации.
4. Построить спектр сигнала.
5. Найти частоту основного пика.
6. Оценить уровень тона.

## Пример структуры MATLAB-скрипта
```matlab
filename = 'tone_capture_iq.bin';
fs = 2.4e6;

fid = fopen(filename, 'rb');
raw = fread(fid, 'int16');
fclose(fid);

i_data = raw(1:2:end);
q_data = raw(2:2:end);

x = double(i_data) + 1j * double(q_data);

Nview = min(length(x), 2000);
t = (0:Nview-1)/fs;

figure;
plot(t, real(x(1:Nview)));
xlabel('Time, s');
ylabel('Amplitude');
title('Real part of IQ signal');
grid on;

Nfft = 4096;
X = fftshift(fft(x(1:Nfft), Nfft));
f = (-Nfft/2:Nfft/2-1)*(fs/Nfft);

figure;
plot(f, 20*log10(abs(X)+1e-12));
xlabel('Frequency, Hz');
ylabel('Magnitude, dB');
title('Spectrum of recorded tone');
grid on;
```
