# Gyro / accelerometer — ICM-42688-P on SPI1

Status: decided (2026-11-22), ERC clean (`gyro.py` → `gyro.net`). Not yet
laid out.

**Changed from the MPU-6000.** The MPU-6000 is end-of-life: Betaflight lists
it as such, accepts it on new boards only when it's genuine, and counterfeits
are common. Betaflight recommends the ICM-42688-P for new designs. It's a
current part with lower gyro noise and a smaller package. The STM32 wiring
(SPI1, CS on PA4, interrupt on PC4) is unchanged; only this block changed.

## What it does

The 6-axis IMU (3-axis gyro + 3-axis accelerometer) that Betaflight
stabilises the quad with. It's the most noise-sensitive part on the board,
so it gets SPI1 to itself and the clean `+3V3_SYS` rail.

## Circuit

| ICM-42688-P pin | Connects to | Note |
|---|---|---|
| 8 VDD | +3V3_SYS, 0.1 µF (C80) + 2.2 µF (C81) | supply range 1.71–3.6 V |
| 5 VDDIO | +3V3_SYS, 10 nF (C82) | matches the STM32's 3.3 V logic |
| 6 GND | GND | |
| 13 AP_SCLK | STM32 PA5 (SPI1_SCK) | SPI up to 24 MHz |
| 1 AP_SDO | STM32 PA6 (SPI1_MISO) | |
| 14 AP_SDI | STM32 PA7 (SPI1_MOSI) | |
| 12 AP_CS | STM32 PA4, 10k pull-up | AP_CS low selects SPI |
| 4 INT1 | STM32 PC4 (EXTI4) | data-ready interrupt |
| 9 INT2/FSYNC/CLKIN | GND | datasheet: GND if FSYNC unused |
| 7 RESV | GND | datasheet: connect to GND |
| 2, 3, 10, 11 RESV | GND | datasheet: no connect or GND |

The pins and external parts are from the TDK InvenSense ICM-42688-P
datasheet (DS-000347): section 4.1, Table 9, and section 4.3, Table 10.
The copy used was revision 1.2. Re-check the tables against the current
revision (1.8) before layout.

## Design choices

- **4-wire SPI** for fast sensor reads in Betaflight's gyro loop.
- **AP_CS pull-up.** The STM32 pin floats until the firmware starts, and
  the pull-up keeps the IMU deselected meanwhile.
- **All reserved pins to ground.** Pin 7 must be grounded. Pins 2, 3, 10 and
  11 may be, and grounding them gives a solid ground under the sensor with
  nothing floating.
- **No external clock.** Pin 9 is grounded and Betaflight runs the sensor
  from its internal oscillator. Some flight controllers feed pin 9 a clock
  for extra accuracy. That's a later option, not needed here.
- **Clean rail.** The ESP32-S3, camera and buck-boost currents never touch
  `+3V3_SYS`.

## Layout (the part that matters most for flight)

- **Position:** put the IMU close to the board's centre and align it square
  to the board edges.
- **Orientation:** record which way pin 1 faces. Betaflight's
  `gyro_1_sensor_align` in the target must match the real orientation, or
  the quad flips on takeoff. The datasheet's pin-out figure shows the +X,
  +Y and +Z sensor axes.
- **Keep away from noise sources:**
  - the buck-boost inductor (L10) and its switching node;
  - the motor FETs and their high-current loops;
  - the ESP32-S3 antenna.
- **Ground:** route no high-current returns under the IMU.
- **Decoupling:** keep C80–C82 tight to their pins.
- **Assembly:** it's a 14-pad LGA with no leads, so it needs machine
  assembly (for example JLCPCB). Students can't hand-solder it.

## Part availability

- **LCSC/JLCPCB part C1850418.** Check stock before committing to a build
  quantity, since TDK supply can be tight.
- **Buy only from authorised distributors.** Counterfeit IMUs are common.

## To verify before layout

- [ ] Re-check pins and parts against the current datasheet revision (1.8).
- [ ] Check the KiCad footprint `LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y`
      against the ICM-42688-P land pattern in the datasheet.
- [x] Betaflight target: `GYRO_1_SPI_INSTANCE` SPI1, CS PA4, EXTI PC4.
      Wiring checked on the fc board; see
      `firmware/betaflight/config/DRONEKITPRO/config.h` and the matching
      CLI lines in `firmware/betaflight/cli-defaults.txt`.
- [x] Sensor alignment from the layout: `CW180FLIP` (bottom-mounted,
      rotation 0). See `firmware/betaflight/cli-defaults.txt`.
- [ ] Confirm the axis figure in the datasheet (pin 1 top-left, +X right,
      +Y up) and bench-check the axes in the Configurator before flight.
