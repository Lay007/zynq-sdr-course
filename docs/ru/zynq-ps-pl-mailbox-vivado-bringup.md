# PS↔PL mailbox в Vivado: первая аппаратная сборка

Эта страница продолжает Lab 5.12 и описывает **минимальный** аппаратный эксперимент Zynq. Здесь нет AD936x, QPSK, DMA и interrupt. Цель одна:

```text
Linux в PS
  ↓
M_AXI_GP0
  ↓
AXI SmartConnect / Interconnect
  ↓
zynq_message_mailbox_vivado_wrapper
  ↓
PL hardware echo
  ↓
те же AXI-регистры
  ↓
Linux в PS
```

Если этот путь не понятен и не работает, подключать радиомодем рано.

## Что уже есть в репозитории

RTL:

```text
blocks/block_05_fpga_hdl_flow/rtl/
  zynq_message_mailbox_axi_lite.v
  zynq_message_mailbox_vivado_wrapper.v
```

Первый файл содержит сам mailbox и hardware echo. Второй фиксирует внешний интерфейс для Vivado:

- AXI4-Lite;
- data width 32 bit;
- address width 32 bit;
- один `s_axi_aclk`;
- synchronous active-low `s_axi_aresetn` внутри mailbox.

Vivado-specific wrapper содержит `X_INTERFACE_INFO` / `X_INTERFACE_PARAMETER`, чтобы сигналы воспринимались как один `S_AXI` bus при использовании Module Reference.

Software:

```text
tools/zynq_message_console.py
```

Тот же helper работает с mock backend на обычном ПК и через `/dev/mem` на Linux в PS.

## 1. Начните с известной рабочей конфигурации PS

Для реальной платы **не создавайте PS7 settings на глаз**. Используйте известный рабочий board project / hardware handoff курса и его DDR/MIO/clock configuration.

В репозитории исходные материалы платы находятся под:

```text
hardware/7020_ad936x_sdr/
```

Для первой PS↔PL лабораторной AD936x datapath не требуется, но корректная конфигурация DDR, MIO и boot всё равно должна соответствовать конкретной плате.

## 2. Добавьте RTL sources

Добавьте в Vivado оба файла:

```text
zynq_message_mailbox_axi_lite.v
zynq_message_mailbox_vivado_wrapper.v
```

В Block Design добавьте `zynq_message_mailbox_vivado_wrapper` как **Module Reference**.

Ожидаемый результат: Vivado группирует AXI-сигналы wrapper в один slave interface `S_AXI`.

Если Vivado показывает только отдельные scalar/vector ports, сначала исправьте interface inference. Не соединяйте десятки AXI-сигналов вручную как учебную норму.

## 3. PS7 configuration

На Zynq Processing System нужны:

- `M_AXI_GP0` — enabled;
- `FCLK_CLK0` — enabled;
- для первого опыта удобно использовать `100 MHz`;
- `FCLK_RESET0_N` — вывести в PL reset path.

Частота 100 MHz здесь не требование mailbox-алгоритма. Это простой учебный baseline, совпадающий с metadata wrapper. Если известная рабочая board configuration использует другую частоту, зафиксируйте её и синхронно поправьте interface metadata.

## 4. Clock и reset

Минимальная структура:

```text
PS7/FCLK_CLK0 ──────────────┬──────── SmartConnect/aclk
                            └──────── mailbox/s_axi_aclk

PS7/FCLK_RESET0_N
        ↓
Processor System Reset
        ↓ peripheral_aresetn
mailbox/s_axi_aresetn
```

Для первой лабораторной **нет CDC**: PS AXI и mailbox работают от одного PL clock.

Это важная образовательная точка. CDC появится только когда интерфейс действительно пересечёт разные clock domains.

## 5. AXI connection

Соедините:

```text
PS7/M_AXI_GP0
      ↓
AXI SmartConnect (или AXI Interconnect)
      ↓
mailbox/S_AXI
```

Затем выполните `Validate Design`.

## 6. Address Editor

Назначьте mailbox memory-mapped range через Vivado Address Editor.

В отчёте запишите:

```text
MAILBOX_BASE = 0x........
range        = ..........
```

**Не используйте адрес из этой страницы:** курс намеренно не фиксирует его. Источник истины — Address Editor конкретной сборки.

Software использует offsets `0x00…0xAC` внутри назначенного range.

## 7. Build и programming evidence

Минимальный пакет evidence:

- screenshot Block Design;
- screenshot Address Editor;
- bitstream/build identity;
- clock frequency;
- physical base address;
- способ загрузки bitstream;
- Linux boot confirmation.

Пока это не сделано на плате, CI/Icarus доказывают только RTL semantics.

## 8. Linux probe

На плате скопируйте `tools/zynq_message_console.py` и сначала только проверьте ID:

```bash
sudo python3 tools/zynq_message_console.py \
  --base <MAILBOX_BASE> probe
```

Ожидается:

```text
id=0x4d424f58 version=0x00010000
```

Если ID не совпадает, **не переходите к message demo**. Сначала проверьте:

- реально ли загружен нужный bitstream;
- правильный ли physical address;
- включён ли GP0;
- работает ли FCLK/reset;
- совпадает ли hardware handoff с Linux image.

## 9. Первый настоящий PS→PL→PS message

После успешного probe:

```bash
sudo python3 tools/zynq_message_console.py \
  --base <MAILBOX_BASE> demo "Hello PL" --sequence 1
```

Ожидаемая идея вывода:

```text
TX sequence=1 bytes=8 payload="Hello PL"
RX sequence=1 bytes=8 crc=OK payload="Hello PL"
```

На этом этапе `crc=OK` означает только успешный **hardware echo contract**: PL помечает корректный echo snapshot как valid. Это ещё не CRC радиопакета и не RF evidence.

## 10. Что студент должен уметь объяснить после PASS

1. Почему Python-программа выполняется в PS, а mailbox state machine — в PL?
2. Почему `MAILBOX_BASE` — physical address, а `0x70` — offset RX data внутри IP?
3. Зачем нужен SmartConnect/Interconnect?
4. Что означает `M_AXI_GP0` с точки зрения направления master/slave?
5. Почему в этой версии нет CDC?
6. Почему hardware echo полезен до подключения QPSK?

## Следующий шаг курса

Только после аппаратного echo заменяем внутреннюю операцию:

```text
TX mailbox → echo → RX mailbox
```

на:

```text
TX mailbox
→ 32-byte packet bridge
→ существующий QPSK modem
→ packet recovery
→ RX mailbox
```

PS helper и пользовательский сценарий при этом должны остаться почти неизменными. Именно это демонстрирует пользу архитектурного разделения PS/PL.
