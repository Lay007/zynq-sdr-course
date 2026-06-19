# Лабораторная 9.4 — Чтение WAV IQ и офлайн-анализ

## Цель

Научиться читать `WAV IQ` запись через manifest, восстанавливать комплексные отсчёты, строить FFT и получать воспроизводимые метрики для реальных захватов.

## Что выполняется

В работе студент:

1. берёт manifest с checksum и локальным path hint;
2. читает двухканальный `WAV IQ` файл;
3. интерпретирует каналы как `I/Q`;
4. считает spectrum, peak, SNR, DC offset и clipping fraction;
5. сохраняет графики и metrics JSON.

## Подробная техническая часть

--8<-- "blocks/block_09_recording_and_analysis_tools/lab_9_4_read_wav_iq_and_analyze.md"
