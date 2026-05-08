# Лабораторная 8.3 — Восстановление символьной синхронизации

## Цель

Понять, как выбор неправильной фазы дискретизации увеличивает EVM/BER, и научиться выбирать лучшую sampling phase для QPSK-сигнала.

## Что выполняется

В работе студент:

1. генерирует oversampled QPSK-сигнал;
2. вносит timing offset;
3. перебирает возможные sampling phases;
4. выбирает фазу с минимальной EVM;
5. сравнивает constellation, EVM и BER до/после timing recovery.

## Результат

После выполнения работы должны быть получены:

- constellation plot при неправильной фазе;
- constellation plot после восстановления timing;
- график EVM versus sampling phase;
- educational eye preview;
- metrics JSON.

## Что приложить к отчёту

- samples per symbol;
- injected timing offset;
- estimated best phase;
- EVM/BER до и после;
- eye preview;
- вывод о роли timing recovery.

## Подробная техническая часть

--8<-- "blocks/block_08_modulation_and_synchronization/lab_8_3_timing_recovery.md"
