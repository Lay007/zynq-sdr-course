# Lab 11.46 — Сообщение из консоли одной Zynq в консоль другой

## Идея

Это не ещё одна лаборатория по BER. Это пользовательский финал основной образовательной линии курса:

```text
board A console
    ↓
PS A
    ↓ AXI-Lite mailbox
PL A: packet source → существующий QPSK TX
    ↓
AD936x A
    ↓ RF / cable
AD936x B
    ↓
PL B: существующий QPSK RX → packet recovery
    ↓ AXI-Lite mailbox
PS B
    ↓
board B console
```

Студент вводит строку на первой плате и видит **ту же строку** на второй.

## Почему эта лаборатория важнее ещё одного DSP-блока

К этому моменту курс уже показывает mapper, RRC, синхронизацию, CFO/timing, BER и двухплатные измерения. Но без пользовательских данных всё это легко воспринимать как набор отдельных экспериментов.

Lab 11.46 связывает их в одну систему:

- PS отвечает за пользовательский интерфейс и packet-level software;
- PL отвечает за детерминированный bit/symbol/sample datapath;
- AXI — реальная граница между ними;
- AD936x переносит уже не тестовый паттерн как самоцель, а понятное сообщение.

## Предпосылки

Перед этой лабораторной должны быть понятны:

1. [Zynq: где заканчивается PS и начинается PL](../../ru/zynq-ps-pl-architecture.md);
2. [Lab 5.12 — PS↔PL message mailbox](lab-5-12-zynq-ps-pl-mailbox.md);
3. существующий двухплатный QPSK тракт и результат Lab 11.45.

## Что переиспользуем

Не строим новый PHY. Переиспользуем доказанный тракт Block 11:

```text
QPSK mapper
→ RRC TX
→ AD936x
→ RX matched filter / timing / carrier recovery
→ frame synchronization
→ recovered bits
```

Новая работа находится **до mapper и после recovered bits**:

```text
PS message bytes → packet serializer → [existing modem] → packet decoder → PS message bytes
```

## Ограничение первой версии

Существующий рабочий кадр использует **256 payload bits = 32 bytes**. Поэтому первая radio-версия принимает сообщения длиной `0…32` bytes.

Это намеренное ограничение baseline, а не недостаток mailbox:

- PS/PL mailbox хранит до 64 bytes;
- v1 radio bridge использует один существующий 32-byte QPSK payload;
- fragmentation/multiple frames — отдельное расширение после первого PASS.

`Hello from board A` помещается в один кадр.

## Packet payload v1

Внутри существующих 32 payload bytes используем простой формат:

```text
byte 0      : payload length N, 0…27
bytes 1..2  : sequence, uint16 little-endian
bytes 3..29 : UTF-8/application bytes, zero padded
bytes 30..31: CRC-16/CCITT over bytes 0..29
```

То есть максимальное пользовательское сообщение v1 — **27 bytes**. Этого достаточно для учебного demo и оставляет packet metadata/CRC внутри уже существующего payload размера.

На первом этапе packet assembly/CRC удобно делать в **PS**. PL получает готовые 32 payload bytes и отвечает за их детерминированную передачу как bits/symbols/samples. На RX PS проверяет CRC и печатает сообщение.

Это специально подчёркивает архитектурное разделение, а не переносит всю систему в FPGA.

## Этап 1 — software contract без RF

Убедиться, что студент понимает mailbox:

```bash
python tools/zynq_message_console.py --mock demo "Hello Zynq" --sequence 17
```

Это не RF simulation. Здесь проверяется только PS-visible interface.

## Этап 2 — одна плата, hardware PS↔PL echo

Собрать mailbox AXI-Lite IP и доказать:

```text
Linux PS → AXI-Lite → PL echo → AXI-Lite → Linux PS
```

Ожидаемый результат:

```text
zynq$ sudo python3 tools/zynq_message_console.py --base <mailbox_addr> send "Hello PL" --sequence 1
TX sequence=1 bytes=8 payload="Hello PL"
```

и чтение того же payload из RX mailbox.

Физический адрес берётся из Vivado Address Editor конкретной сборки.

## Этап 3 — цифровой modem loopback

Заменить PL echo на packet serializer + существующий QPSK digital loopback:

```text
PS → mailbox → packet bytes → QPSK TX → digital loopback → QPSK RX → mailbox → PS
```

Здесь RF ещё нет, но уже проверяется правильность packet framing поверх реального modem datapath.

## Этап 4 — две платы

Начать с безопасного кабельного соединения и требуемого затухания, затем при необходимости перейти к OTA.

Board A:

```text
board-a$ sudo python3 tools/zynq_message_console.py --base <addr> send \
  "Hello from board A" --sequence 17
TX sequence=17 bytes=18 payload="Hello from board A"
```

Board B:

```text
board-b$ sudo python3 tools/zynq_message_console.py --base <addr> receive --wait 10
RX sequence=17 bytes=18 crc=OK payload="Hello from board A"
```

Это и есть основной acceptance criterion.

## Что фиксировать в отчёте

- bitstream / build identity обеих плат;
- mailbox physical base address;
- RF frequency, sample rate, attenuation/gain settings;
- исходную строку и UTF-8 byte length;
- sequence;
- RX CRC result;
- число повторов;
- packet success rate;
- при ошибке — raw 32-byte payload или hex dump, а не только «не работает».

## Минимальная кампания

После первого успешного сообщения выполнить не менее 100 коротких передач одного payload и сохранить:

```text
packets sent
packets received
CRC OK
CRC failed / timeout
PER
```

BER из существующего modem evidence остаётся полезен, но здесь главным пользовательским показателем становится **PER / successful message delivery**.

## Что не нужно делать до первого PASS

Не добавлять одновременно:

- DMA;
- interrupts;
- variable-length streaming protocol;
- fragmentation;
- encryption;
- OFDM;
- LoRa;
- Ethernet bridge.

Сначала должна пройти самая простая наблюдаемая цепочка:

```text
text → PS → PL → RF → PL → PS → text
```

## Критерий завершения

Лабораторная завершена только когда есть **hardware evidence** с двух плат:

1. команда передачи на Board A;
2. принятая строка на Board B;
3. `sequence` совпадает;
4. `CRC=OK`;
5. задокументированы RF-настройки;
6. короткая повторная кампания даёт измеренный PER.

До этого любые mock/RTL/digital-loopback результаты считаются промежуточными доказательствами, а не готовой двухплатной радиолинией сообщений.
