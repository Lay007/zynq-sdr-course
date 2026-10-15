# Лабораторная 11.46 — Сообщение из консоли одной Zynq в консоль другой

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

Существующий рабочий кадр использует **256 payload bits = 32 bytes**. Поэтому первая radio-версия передаёт один фиксированный 32-байтный payload пакета; сообщение пользователя в нём — до 27 bytes (см. Packet payload v1).

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

Численные соглашения зафиксированы явно:

| Параметр | Соглашение packet-v1 |
|---|---|
| Вариант CRC | CRC-16/CCITT-FALSE |
| Полином | `0x1021` |
| Начальное значение | `0xffff` |
| `refin` / `refout` | `false` / `false` |
| Финальный XOR | `0x0000` |
| Стандартная проверка | `CRC("123456789") = 0x29b1` |
| Порядок байтов sequence и CRC | little-endian |
| Байтовые линии 256-bit bus | packet byte `n` отображается в `payload[8*n +: 8]` |
| Сериализация битов | сначала младший бит каждого байта |

Mailbox уже упаковывает байты little-endian в 32-битные слова, поэтому на
границе PS/PL не требуется дополнительный word swap.

В первой реализации на плате packet assembly и окончательное решение по CRC можно оставить в **PS**. Синтезируемый codec служит исполняемой перекрёстной проверкой и позволяет собрать автономный RTL loopback из mailbox fields; при AXI-интеграции нужно выбрать одну границу и не кодировать уже собранный packet повторно. PL детерминированно передаёт итоговые 32 payload bytes как bits/symbols/samples.

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

В репозитории теперь есть исполняемый baseline этапа 3:

- `qpsk_packet_v1.py` — независимый Python reference для packet/CRC;
- `qpsk_packet_v1_codec.v` — синтезируемый ready/valid packet codec;
- `qpsk_packet_frame_bridge.v` — добавляет существующую 24-битную преамбулу и
  собирает нормализованные 256 payload bits после существующего frame sync;
- `qpsk_packet_digital_loopback.v` — переиспользует существующие mapper, RRC TX,
  matched filter, timing sampler, hard decision и quadrant-resolving frame sync;
- `tb_qpsk_packet_digital_loopback.sv` — передаёт `"Hello from board A"`,
  sequence `17` и требует тот же payload с `CRC=OK`.

Запуск сфокусированной регрессии:

```bash
python tools/run_block5_hdl_smoke.py --no-generate \
  --test tb_qpsk_packet_v1_codec \
  --test tb_qpsk_packet_digital_loopback
```

Корректная формулировка результата:

```text
packet digital loopback PASS
```

Все новые packet-блоки используют один clock, синхронный active-high reset и
ready/valid transfer. Producer удерживает payload стабильным при `valid=1` и
`ready=0`; этот baseline не добавляет CDC.

Этот результат **не доказывает** AXI/Vivado integration, FPGA synthesis/timing,
RF transport или двухплатный link.

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

### Как это прошло на стенде курса (14.10.2026)

Первое сообщение между двумя платами прошло по проводному радиотракту более коротким путём, чем
описанный выше. Использовано то, что уже работает на железе:

- **Плата A** через `iio_writedev` передаёт кадр Лабораторной 11.45, в котором 256 бит полезной
  нагрузки и есть пакет packet-v1.
- **Плата B** принимает его модемом в ПЛИС. ПК читает принятые биты из регистра декодированных бит
  моста (`gp_ctrl[16]`) и проверяет CRC.

```text
python blocks/block_11_integrated_sdr_project/python/two_board_message.py send "Hello from board A" --sequence 17 --whiten
TX sequence=17 bytes=18 payload="Hello from board A"
RX sequence=17 bytes=18 crc=OK payload="Hello from board A"
```

Десять сообщений по 20 приёмов: доставлено без искажений 189 из 200, PER 5,5 %. Все 11 неудач
либо не дали захвата кадра, либо были пойманы CRC; ни одно искажённое сообщение не принято
([отчёт](https://github.com/Lay007/zynq-sdr-course/blob/main/reports/hardware/two-board-message-20261014.md)).

Два урока по дороге:

- Дифференциальный кадр нельзя просто повторять, если суммарное приращение его фазы не равно целому
  обороту: иначе на каждом стыке кадров возникает скачок фазы, который ломает следующую преамбулу.
- Пакет, дополненный нулями, превращается в длинную серию одного и того же символа. Скремблирование
  полезной нагрузки PN9 (на обоих концах) это исправило: 24 из 24 вместо 17 из 24.


С консолей самих плат, без Python на платах: `sw/zmsg.c`, собранная `arm-linux-gnueabihf-gcc -static`
из Vitis, делает то же самое на обоих концах.

```text
board-a$ ./zmsg send "Hello from board A" --seq 17
TX sequence=17 bytes=18 payload="Hello from board A"
board-b$ ./zmsg receive
RX sequence=17 bytes=18 crc=OK payload="Hello from board A"
board-a$ ./zmsg stop
```

Десять сообщений по 20 приёмов с консолей: доставлено 199 из 200, одна ошибка CRC, ни одного
неверного сообщения не принято (перемерено 15.10.2026). Первый замер, 200 из 200, сделан версией
`zmsg`, которая иногда теряла импульс старта и тогда заново читала предыдущий кадр. При передатчике,
повторяющем одно сообщение, это может только превратить пропущенный приём в засчитанный, поэтому
после исправления число проверено заново (см. Лабораторную 11.48).

Плата A здесь повторяет сообщение циклически, и каждый приём на плате B ловит одну из многих копий.
Чтобы передать сообщение один раз, как это делает настоящее радио, нужен приёмник, который его
ждёт: это Лабораторная 11.48, `zmsg send --once` и `zmsg receive --listen`.

Что на этом этапе ещё открыто: mailbox PS/PL, передающий пакет модему. Mailbox проходит
собственную проверку эхом на плате A (Лабораторная 5.12), но сообщение выше идёт от консоли к модему
без него.

## Что фиксировать в отчёте

- bitstream / build identity обеих плат;
- mailbox physical base address;
- RF-частоту, частоту дискретизации, настройки аттенюации/усиления;
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
