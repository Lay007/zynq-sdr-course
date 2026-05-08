# Лабораторная 8.2 — Оценка и коррекция фазового смещения

## Цель

Научиться компенсировать постоянный поворот QPSK-созвездия после устранения частотного рассогласования.

## Что выполняется

В работе студент:

1. генерирует QPSK-сигнал;
2. вносит постоянное фазовое смещение;
3. оценивает фазу слепым методом четвёртой степени;
4. уточняет фазу decision-directed методом;
5. сравнивает EVM и BER до/после коррекции.

## Результат

После выполнения работы должны быть получены:

- constellation plot до коррекции;
- constellation plot после blind correction;
- constellation plot после decision-directed refinement;
- график сравнения EVM;
- metrics JSON.

## Что приложить к отчёту

- true phase offset;
- blind phase estimate;
- decision-directed estimate;
- EVM/BER до и после;
- объяснение ambiguity `pi/2`;
- инженерный вывод.

## Подробная техническая часть

--8<-- "blocks/block_08_modulation_and_synchronization/lab_8_2_phase_offset_correction.md"
