# Лабораторная 7.3 — Метрики TX/RX loopback

## Цель

Собрать компактную синтетическую QPSK-модель TX/RX loopback и рассчитать ключевые метрики качества: EVM, SNR и BER.

## Что выполняется

В работе студент:

1. генерирует случайные биты и QPSK-символы;
2. моделирует TX frequency offset и канал с шумом;
3. выполняет DDC-коррекцию;
4. принимает решения по символам;
5. строит constellation plots и рассчитывает EVM/BER.

## Результат

После выполнения работы должны быть получены:

- spectrum plot до/после DDC;
- TX и RX constellation plots;
- metrics JSON;
- численные значения EVM, SNR estimate и BER.

## Что приложить к отчёту

- параметры QPSK-модели;
- sample rate и samples per symbol;
- TX offset и DDC shift;
- constellation plots;
- таблицу EVM/SNR/BER;
- вывод о готовности к real RF captures.

## Подробная техническая часть

--8<-- "blocks/block_07_tx_rx_chains/lab_7_3_tx_rx_loopback_metrics.md"
