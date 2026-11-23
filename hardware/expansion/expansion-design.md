# Expansion headers — six plug-in ports

Status: decided, ERC clean (`expansion.py` → `expansion.net`). Not yet laid
out.

Six small **JST-SH 1.0 mm** headers for add-on modules. **Four connect to the
STM32** (flight side: Betaflight in Mode A). **Two connect to the ESP32-S3**
(student code in Mode B).

## The headers

| Ref | Name | Pins (in connector order) | MCU pins | For |
|---|---|---|---|---|
| J130 | SENSOR | GND, 3V3, SDA, SCL | STM32 I2C1: PB7 SDA, PB6 SCL (shared with the baro) | ToF / flow board in the rear sensor bay, any Qwiic sensor |
| J131 | UART3 | GND, PWR, TX, RX | STM32 USART3: PB10 TX, PB11 RX | GPS, UART optical flow, telemetry |
| J132 | LED | GND, PWR, DIN | STM32 PA8 (TIM1_CH1) | WS2812 LED strip |
| J133 | PWM | GND, PWR, PWM1–4 | STM32 PC6–PC9 (TIM8_CH1–4) | servos, gripper, extra outputs |
| J134 | CODE-I2C | GND, 3V3, SDA, SCL | ESP32-S3 GPIO47 SDA, GPIO48 SCL | Qwiic sensors for student code |
| J135 | CODE-IO | GND, 3V3, IO21, IO38, IO39, IO40 | ESP32-S3 GPIO21/38/39/40 | buttons, LEDs, PWM, one-wire from student code |

- **3V3** on these headers is `+3V3_ESP`.
- **PWR** is `+3V8`. There's no 5 V on the board.
- **TX/RX** are named from the flight controller's side. TX goes to the
  module's RX.

## Design choices

- **Split by MCU.** In Mode B the student's Python runs on the ESP32-S3, so
  its modules plug straight into ESP pins. Routing them through the STM32
  and MSP would make simple sensor code painful. Flight add-ons (GPS, flow,
  LEDs) need Betaflight, so they go to the STM32.
- **Qwiic / STEMMA QT pin order on both I2C headers.** That's GND, 3V3, SDA,
  SCL on a 4-pin JST-SH, so off-the-shelf Qwiic sensors plug straight in
  with a standard cable. That's a big win for students.
- **Header power:**
  - 3.3 V comes from `+3V3_ESP` (the 1 A LDO), never the gyro's
    `+3V3_SYS`. External modules' current and noise stay off the gyro rail.
  - `+3V8` feeds the UART, LED and PWM headers, for modules with their own
    regulators and for WS2812 LEDs.
  - Budget about 200 mA total across all headers. See the power doc.
- **100 Ω in series with every signal.** It protects the MCU pins from
  wiring mistakes and hot-plugging. The resistors can be 4 × 0402 arrays at
  layout to save space.
- **I2C pull-ups:**
  - J130 shares I2C1, whose 5.1k pull-ups are in the baro block. Don't add
    more.
  - J134 has its own 4.7k pull-ups to `+3V3_ESP`.
  - Qwiic boards often carry their own pull-ups too. Cut their jumper if
    several boards are chained.
- **1 µF at each header's power pin.**

## Firmware notes

- **Betaflight:**
  - UART3 is a serial port: GPS, MSP or telemetry.
  - `resource LED_STRIP 1 A08`.
  - The PWM outputs are `resource SERVO 1..4` on C06–C09, or PINIO.
  - The SENSOR header is I2C1. Betaflight only drives devices it knows; the
    baro sits on the same bus.
- **ESP32-S3:** in student code, use `Wire.begin(47, 48)` or
  `machine.I2C(sda=47, scl=48)` for CODE-I2C. GPIO21 and 38–40 are plain
  digital I/O with PWM through LEDC.
- GPIO39 and 40 double as the ESP32-S3's JTAG pins (MTCK, MTDO). That's
  fine as GPIO, but they're unavailable if you ever use JTAG debugging.

## Still free

- **STM32:** PA0, PA1, PC0, PC2, PC3 (ADC-capable), PC5, PD2, PB3, PC14 and
  PC15 (low-drive, inputs), and the SPI3 bank (PC10–PC12, PA15, PB13–PB15).
- **ESP32-S3:** GPIO35–37. These are free on the N8R2's quad PSRAM; the
  octal "R8" variants would use them.

## To verify before layout

- [ ] **Board space.** Six JST-SH connectors plus their resistors take
      roughly 150–200 mm². The 32 × 30 mm board is already tight, so check
      the fit in layout. Ports can be downgraded to solder pads if needed.
- [ ] Confirm a WS2812 strip runs reliably at 3.8 V supply with 3.3 V data.
- [ ] Check that the ESP32-S3's GPIO21 and 38–40 have no conflicting use in
      the final firmware.
