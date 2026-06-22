# Dual-boot control circuit — design and verification

Status: paper design, not yet captured in KiCad, not yet built.
This is the gate. Verify here before any layout.

## What it has to do

| | Mode A (Fly) | Mode B (Code) |
|---|---|---|
| Boot switch | LOW | HIGH |
| STM32F405 | Flight controller (Betaflight) | Motor co-processor (takes setpoints from ESP32 over MSP) |
| ESP32 | OFF, held in reset | WiFi AP, runs user code |
| Who is in charge | RC radio via ELRS | ESP32 |

The STM32 runs in both modes. The boot switch does not swap STM32 firmware.
In Mode B, Betaflight keeps doing stabilisation and mixing but takes its RC
setpoints from the ESP32 over MSP instead of from the ELRS receiver. The boot
switch's real jobs: (1) tell the STM32 which RC source to use, (2) gate whether
the ESP32 is allowed to boot at all.

## Power-on sequencing (the fail-safe)

STM32 GPIOs come up as floating inputs before firmware runs. If the ESP32 EN
line had the usual pull-UP, the ESP32 would boot at power-on regardless of mode,
possibly with props fitted. So EN gets a pull-DOWN: dark by default.

1. Power applied. STM32 GPIO floats. EN held LOW by 10k pulldown. ESP32 OFF.
2. STM32 boots (fast), reads the mode switch.
3. Mode A: STM32 leaves EN low (or actively drives low). ESP32 stays OFF.
   Mode B: STM32 drives EN HIGH. ESP32 boots, reading its OWN strapping resistors.

Dark-by-default is the correct failure state for a flying machine.

## Net list (this sub-circuit)

| Net | From | To | Components | Notes |
|---|---|---|---|---|
| MODE_SENSE | Boot switch | STM32 GPIO (in) | 10k pull + 100nF debounce | Proposed pin PC4. Read once at init. |
| ESP_EN | STM32 GPIO (out, push-pull) | ESP32 EN | 10k pulldown to GND, 100nF to GND | Default OFF. STM32 drives HIGH for Mode B. |
| BRIDGE_TX | STM32 USART TX | ESP32 GPIO16 (U2RXD) | series 100R optional | Use ESP32 UART2, not UART0. |
| BRIDGE_RX | STM32 USART RX | ESP32 GPIO17 (U2TXD) | series 100R optional | UART2 = non-strapping pins. |
| STM_BOOT0 | ESP32 GPIO (out) | STM32 BOOT0 | 10k pulldown to GND | Default LOW (flash boot). ESP32 drives HIGH only to flash STM32. |
| STM_NRST | ESP32 GPIO (open-drain) | STM32 NRST | STM32 internal pullup + 100nF | ESP32 pulses LOW to reset STM32 into bootloader. |

Proposed STM32 pins are placeholders. Reconcile MODE_SENSE, ESP_EN and the
bridge UART against the Betaflight STM32F405 target resource map before layout.

## ESP32 strapping pins — verification

The STM32 must touch NONE of these. Each gets its own resistor; the ESP32 reads
them itself when EN rises.

| Pin | Required at boot | Resistor | Why |
|---|---|---|---|
| GPIO0 | HIGH (flash boot) | 10k pull-up | LOW = download mode. Program button pulls it low. |
| GPIO2 | LOW / floating | 10k pull-down | Blue LED to GND is fine. Must not be high at boot. |
| GPIO12 (MTDI) | LOW | 10k pull-down | Selects 3.3V flash. HIGH = 1.8V = boot fails. Critical. |
| GPIO15 (MTDO) | HIGH | 10k pull-up | LOW changes boot behaviour. |
| GPIO5 | HIGH | 10k pull-up (default) | SDIO timing. Default fine. |

Rule: confine STM32-to-ESP32 wiring to EN, the UART2 bridge, and the two
flash-control lines that originate on the ESP32 side. Nothing on GPIO0/2/12/15.

## Open risk — 3.3V supply current (read this before layout)

The documented power tree is XT30 -> MP2307 buck (5V) -> RT9013 LDO (3.3V).
The RT9013 is a 500mA part. The ESP32 alone wants a 3.3V rail rated for ~500mA
because WiFi TX draws current spikes up to ~500mA. Feeding STM32 + sensors +
ESP32 WiFi from one 500mA LDO is very likely to brown out on TX bursts. This is
the same class of failure as the SIM800L telemetry brownouts.

Options to resolve:
- Higher-current 3.3V regulator (buck or 800mA+ LDO), or
- Separate 3.3V regulator dedicated to the ESP32, plus a bulk cap (10uF+)
  right at the ESP32 3V3 pin.

This must be decided before layout because it changes the power section.

## Firmware implications (not free, flag for planning)

- Betaflight needs a small custom target change: read MODE_SENSE at init, drive
  ESP_EN, and select RC source (ELRS vs MSP-over-UART) by mode.
- The ESP32 -> STM32 OTA flash path implements the STM32 system bootloader
  protocol over the bridge UART (toggle BOOT0 high, pulse NRST, send firmware).

## Sub-circuit BOM

| Qty | Part | Value | Note |
|---|---|---|---|
| 6 | Resistor 0402 | 10k | strapping + EN + BOOT0 pulls |
| 2 | Resistor 0402 | 100R | optional UART series |
| 3 | Cap 0402 | 100nF | EN, NRST, debounce |
| 1 | Cap 0805 | 10uF | ESP32 3V3 bulk |
| 1 | Switch | SPDT slide | boot mode |
| 1 | Tactile button | - | ESP32 GPIO0 program |

## To verify before moving on

- [ ] Confirm RT9013 vs ESP32 current; pick the 3.3V solution.
- [ ] Map MODE_SENSE / ESP_EN / bridge UART to free STM32F405 pins not used by Betaflight.
- [ ] Confirm the ESP32 program/reset method (USB-UART vs pads) and that it does not collide with the STM32 bridge.
- [ ] Confirm GPIO2 is the intended ESP32 status LED and the LED wiring keeps it low at boot.
