# Лабораторная 6.8 — OTA DDS tone-наблюдение на stock-shell Zynq

## Цель

Передать короткий DDS-generated tone через `TX1`, принять его на `RX1` по
воздуху и сохранить результат как воспроизводимый `CI16` датасет для
офлайн-проверки через Block 9.

## Что выполняется

В работе студент:

1. использует stock-shell `Zynq-7020 + AD9361`, где уже живы `ad9361-phy`, DDS и RX capture;
2. задает `LO`, sample rate, bandwidth, RX gain и TX attenuation с хоста по `IIO`;
3. включает квадратичный DDS tone на `TX1_I_F1` и `TX1_Q_F1`;
4. снимает короткий `CI16` захват с `cf-ad9361-lpc`;
5. оформляет manifest с checksum, частотным планом и окном поиска тона;
6. проверяет результат офлайн-анализатором `Lab 9.2`.

## Результат

После выполнения работы должны быть получены:

- реальный `CI16` IQ-файл OTA tone-захвата;
- manifest датасета;
- FFT-график и time preview;
- measured peak, frequency error и SNR;
- инженерный вывод о готовности stock-shell RF тракта к первому BPSK handoff.

## Что приложить к отчету

- manifest tone-датасета;
- частоту LO, tone offset, sample rate и bandwidth;
- RX gain и TX attenuation;
- checksum IQ-файла;
- спектр и time preview из офлайн-ридера;
- краткий вывод, что именно уже доказано для пути `TX -> RF -> RX`.

## Подробная техническая часть

--8<-- "blocks/block_06_rf_frontend_and_ad9363/lab_6_8_zynq_ota_tone_observation.md"
