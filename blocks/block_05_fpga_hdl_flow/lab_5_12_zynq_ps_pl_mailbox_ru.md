# Lab 5.12 — PS↔PL message mailbox: первый осмысленный мост Zynq

## Цель

Понять архитектуру Zynq не через большой Vivado Block Design, а через маленький наблюдаемый обмен:

```text
Linux/Python в PS
      ↓ memory-mapped AXI-Lite
64-byte TX/RX mailbox в PL
      ↓
простая PL-операция / будущий modem datapath
```

После лабораторной студент должен уметь ответить на четыре вопроса:

1. какой код выполняется ARM-процессором;
2. какая логика реализуется в FPGA fabric;
3. как PS видит PL-регистры в адресном пространстве;
4. почему control plane и sample datapath — разные интерфейсы.

Перед работой прочитайте [Zynq: где заканчивается PS и начинается PL](/zynq-sdr-course/ru/zynq-ps-pl-architecture/).

## Почему здесь нет DMA

DMA будет позже. Для первого опыта сообщение ограничено **64 байтами** и хранится прямо в AXI-Lite регистрах. Это не производительная архитектура, зато каждый шаг можно увидеть:

```text
byte → 32-bit register → AXI write → PL state → AXI read → byte
```

Когда этот путь станет понятен, переход к BRAM, AXI4-Stream, DMA и interrupt будет мотивированным, а не механическим.

## Учебный mailbox contract

### Идентификация и управление

| Offset | Register | Access | Meaning |
|---:|---|---|---|
| `0x00` | `ID` | RO | `0x4D424F58` = `MBOX` |
| `0x04` | `VERSION` | RO | `0x00010000` |
| `0x08` | `CONTROL` | WO/W1P | bit0 `TX_START`, bit1 `RX_ACK` |
| `0x0C` | `STATUS` | RO | bit0 `TX_BUSY`, bit1 `TX_DONE`, bit2 `RX_VALID`, bit3 `RX_OVERFLOW` |

### TX mailbox

| Offset | Register | Access | Meaning |
|---:|---|---|---|
| `0x10` | `TX_SEQUENCE` | RW | packet sequence number |
| `0x14` | `TX_LENGTH` | RW | payload length, `0…64` bytes |
| `0x20…0x5C` | `TX_DATA[0…15]` | RW | 64 payload bytes packed little-endian into 16 words |

### RX mailbox

| Offset | Register | Access | Meaning |
|---:|---|---|---|
| `0x60` | `RX_SEQUENCE` | RO | received sequence number |
| `0x64` | `RX_LENGTH` | RO | received payload length |
| `0x68` | `RX_META` | RO | bit0 `CRC_OK`, bit1 `FRAME_ERROR` |
| `0x70…0xAC` | `RX_DATA[0…15]` | RO | received payload |

### Критический контракт RX

Когда `RX_VALID=1`, PL **не изменяет** `RX_SEQUENCE`, `RX_LENGTH`, `RX_META` и `RX_DATA`, пока PS не выполнит `RX_ACK`.

Это делает многословное чтение coherent без сложного snapshot-протокола.

Если новый пакет приходит при занятом mailbox, первая версия интерфейса сохраняет старый пакет и устанавливает `RX_OVERFLOW`. Политика должна быть видима студенту, а не скрыта.

## Упаковка байтов

Строка `ABCD` представляется как четыре ASCII bytes:

```text
41 42 43 44
```

и попадает в `TX_DATA[0]` как little-endian word:

```text
0x44434241
```

Это полезное место, чтобы впервые обсудить endianness на реальном PS/PL интерфейсе.

## Часть A — выполнить без платы

В репозитории используется:

```bash
python tools/zynq_message_console.py --mock demo "Hello Zynq" --sequence 17
```

Mock backend моделирует регистровый контракт, а не RF. Ожидаемая идея вывода:

```text
TX sequence=17 bytes=10 payload="Hello Zynq"
RX sequence=17 bytes=10 crc=OK payload="Hello Zynq"
```

Задача этой части — понять software-visible protocol до Vivado.

## Часть B — первая аппаратная реализация

Минимальный Vivado design:

```text
Zynq7 Processing System
        |
   M_AXI_GP0
        |
AXI Interconnect / SmartConnect
        |
PS/PL mailbox AXI-Lite IP
```

Требования:

- один общий AXI clock для первого опыта;
- reset от стандартной processor-system-reset схемы;
- адрес mailbox назначается через Vivado Address Editor;
- адрес **не копируется из инструкции вслепую** — он записывается в отчёт из конкретной сборки.

На этом этапе PL может делать простой hardware echo: после `TX_START` копировать TX mailbox в RX mailbox и устанавливать `RX_VALID`.

Так студент сначала доказывает:

```text
PS → AXI → PL → AXI → PS
```

без RF и без DSP.

### Конкретная Vivado-процедура (собрана в Vivado 2021.1; на плату не загружалась)

RTL-часть этого шага закоммичена и проверяется в CI (`zynq_message_mailbox_axi_lite.v`, `zynq_message_mailbox_vivado_wrapper.v`, `tb_zynq_message_mailbox_axi_lite.sv`, workflow `block5_ps_pl_mailbox.yml`). Процедура Block Design ниже выполнена целиком 2026-09-24 в Vivado 2021.1 — до bitstream и XSA — одной командой:

```bash
python tools/build_block5_mailbox_bd.py --build-dir C:/tmp/mb
```

Скрипт берёт собственные настройки PS7 платы курса (все 876 параметров `PCW_*`: DDR, MIO, периферия) из её проверенного hardware handoff `hardware/7020_ad936x_sdr/ps/bringup_tests/design_1_wrapper.xsa`, так что DDR и MIO не угадываются, и затем запускает `tools/vivado_block5_mailbox_bd.tcl`. Каталог сборки держите коротким: Vivado предупреждает при пути длиннее 80 символов, а генерация IP ломается у предела Windows в 260 символов.

```tcl
# 1. Новый BD в проекте для xc7z020clg400-2.
create_bd_design "mailbox_echo_bd"

# 2. Zynq PS. У платы курса нет board-файла Vivado, поэтому board preset не
#    применяется; вместо него применяются собственные PCW_* платы (это делает скрипт).
create_bd_cell -type ip -vlnv xilinx.com:ip:processing_system7:5.5 processing_system7_0
apply_bd_automation -rule xilinx.com:bd_rule:processing_system7 \
    -config {make_external "FIXED_IO, DDR" apply_board_preset "0"} \
    [get_bd_cells processing_system7_0]
#    ... set_property CONFIG.<PCW_*> для каждого параметра платы, затем поверх
#    включается то, что нужно лабе (в образе платы M_AXI_GP0 выключен, FCLK0 = 50 МГц):
set_property -dict [list CONFIG.PCW_USE_M_AXI_GP0 {1} CONFIG.PCW_EN_CLK0_PORT {1} \
    CONFIG.PCW_EN_RST0_PORT {1} CONFIG.PCW_FPGA0_PERIPHERAL_FREQMHZ {100}] \
    [get_bd_cells processing_system7_0]

# 3. Mailbox как Verilog module reference (тот же wrapper, который iverilog
#    elaborate'ит в CI).
create_bd_cell -type module -reference zynq_message_mailbox_vivado_wrapper mailbox_0

# 4. M_AXI_GP0 -> interconnect -> S_AXI mailbox; automation добавляет
#    interconnect и блок processor-system-reset.
apply_bd_automation -rule xilinx.com:bd_rule:axi4 \
    -config {Master "/processing_system7_0/M_AXI_GP0" Clk "Auto"} \
    [get_bd_intf_pins mailbox_0/S_AXI]

# 5-6. Дать Vivado назначить адрес, ограничить его 4K (карта регистров 0x00-0xAC),
#      затем провалидировать.
assign_bd_address
set_property range 4K [get_bd_addr_segs {processing_system7_0/Data/SEG_mailbox_0_reg0}]
validate_bd_design

# 7. Прочитать назначенный адрес (в Tcl нет конвейеров, поэтому никакого `| grep`):
set seg [get_bd_addr_segs -of_objects [get_bd_addr_spaces processing_system7_0/Data]]
puts "[get_property OFFSET $seg] [get_property RANGE $seg]"
#    затем make_wrapper, launch_runs impl_1 -to_step write_bitstream -jobs 1,
#    write_hw_platform -fixed -include_bit.
```

Результат этой сборки (нормализованные отчёты в [`reports/fpga/block5_mailbox_bd_raw`](https://github.com/Lay007/zynq-sdr-course/tree/main/reports/fpga/block5_mailbox_bd_raw)):

| Пункт | Значение |
|---|---|
| Сегмент mailbox | `SEG_mailbox_0_reg0`, offset `0x40000000`, range `0x1000` (4 КБ) |
| FCLK_CLK0 | 100,000 МГц |
| Тайминг на 100 МГц | WNS +3,508 нс, 0 нарушающих конечных точек |
| Ресурсы | 1060 LUT, 1844 FF, 0 BRAM, 0 DSP (mailbox 636 LUT / 1265 FF, AXI interconnect 407 LUT) |
| DRC | 0 нарушений |
| Выходы | bitstream и XSA (не закоммичены, на плату не загружались) |

Что показало выполнение рецепта:

- **Без шага 6 mailbox получает всё окно `M_AXI_GP0` в 1 ГБ** (range `0x40000000`). Ограничение 4K — не косметика.
- `apply_board_preset "1"` требует board-файл Vivado, которого у этой платы нет; настройки платы должны браться из её собственного hardware handoff.
- В эталонном образе платы `M_AXI_GP0` выключен, а `FCLK_CLK0` равен 50 МГц, поэтому их нужно включать поверх настроек платы.
- 10 из 876 параметров платы — производные, только для чтения (тактовые частоты шин `*_FREQMHZ` и `PCW_NUM_F2P_INTR_INPUTS`); Vivado отвергает их с CRITICAL WARNING, и это ожидаемо.
- При четырёх параллельных заданиях на машине с 16 ГБ синтез IP упёрся в нехватку памяти; по одному заданию сборка завершается.

`0x40000000` — просто начало окна `M_AXI_GP0`, поэтому Vivado его и выбрал. Это всё равно факт конкретной сборки: записывайте адрес, который сообщит ваша сборка, а не этот.

## Часть C — переход к радиолинии

После hardware echo software API не меняется. Меняется только PL между TX и RX mailbox:

```text
TX mailbox
   ↓
packet serializer / framing
   ↓
существующий QPSK TX datapath
   ↓ RF
существующий QPSK RX datapath
   ↓
packet recovery
   ↓
RX mailbox
```

Это и есть важный образовательный переход: **консоль и PS-код остаются теми же, а datapath внутри PL становится настоящим радиомодемом**.

## Что проверить

- [ ] объяснить PS и PL своими словами;
- [ ] прочитать `ID=MBOX`;
- [ ] показать physical base address из Vivado;
- [ ] передать сообщение длиной 1, 4 и 64 байта;
- [ ] показать little-endian packing минимум одного слова;
- [ ] показать, что `RX_VALID` держит сообщение до `RX_ACK`;
- [ ] объяснить, почему 65 байт должны быть отвергнуты;
- [ ] отдельно отметить, что AXI-Lite mailbox не предназначен для IQ sample stream.

## Вопросы для отчёта

1. Почему mapper/RRC лучше оставить в PL, а `printf()` — в PS?
2. Почему нельзя использовать AXI-Lite для непрерывного IQ-потока?
3. Что произойдёт, если PS читает RX payload, а PL одновременно его перезаписывает?
4. Зачем нужен `RX_ACK`?
5. В какой момент станет оправдан DMA?

## Критерий завершения

Минимальный образовательный PASS:

```text
PS software → AXI-Lite mailbox → PL echo → AXI-Lite mailbox → PS console
```

Следующий уровень курса заменяет `PL echo` настоящим двухплатным QPSK трактом, но сохраняет тот же пользовательский сценарий: **ввести строку на одной плате и увидеть её на второй**.
