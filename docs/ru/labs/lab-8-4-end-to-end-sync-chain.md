# Лабораторная 8.4 — Полная цепочка синхронизации

## Цель

Объединить timing offset, CFO, phase offset и шум в одной QPSK-модели и проверить staged receiver: timing recovery, CFO correction, phase correction и расчёт BER/EVM.

## Что выполняется

В работе студент:

1. генерирует oversampled QPSK-сигнал;
2. вносит несколько impairment одновременно;
3. выполняет timing phase search;
4. оценивает и компенсирует CFO;
5. компенсирует фазовое смещение;
6. сравнивает EVM/BER по этапам.

## Результат

После выполнения работы должны быть получены:

- raw constellation;
- constellation после timing recovery;
- final synchronized constellation;
- график EVM по стадиям;
- BER summary;
- metrics JSON.

## Что приложить к отчёту

- все внесённые impairments;
- порядок staged receiver;
- timing/CFO/phase estimates;
- EVM by stage;
- BER до/после;
- вывод о готовности к real RF receiver chain.

## Подробная техническая часть

--8<-- "blocks/block_08_modulation_and_synchronization/lab_8_4_end_to_end_sync_chain.md"
