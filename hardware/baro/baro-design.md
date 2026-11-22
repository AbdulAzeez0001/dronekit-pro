# Barometer — BMP280 on I2C1

Status: decided, ERC clean (`baro.py` → `baro.net`). Not yet laid out.

## What it's for

- **Mode A (Fly):** Betaflight uses the baro for altitude in the OSD and
  logs, and for its altitude features.
- **Mode B (Code):** the ESP32-S3 can read altitude from the STM32 over MSP,
  which gives student code a "hold this height" building block.

## Circuit

| BMP280 pin | Connects to | Why |
|---|---|---|
| 8 VDD, 6 VDDIO | +3V3_SYS, 100 nF each at the pins | clean rail; pressure readings pick up supply noise |
| 1, 7 GND | GND | |
| 4 SCK | STM32 PB6 (I2C1_SCL), 4.7k pull-up | |
| 3 SDI | STM32 PB7 (I2C1_SDA), 4.7k pull-up | |
| 2 CSB | +3V3_SYS | high = I2C mode |
| 5 SDO | GND | address 0x76, Betaflight's default |

Pinout is from the Bosch BMP280 datasheet: 8-pin LGA, 2.0 × 2.5 mm,
1 GND, 2 CSB, 3 SDI, 4 SCK, 5 SDO, 6 VDDIO, 7 GND, 8 VDD.

## Design choices

- **I2C, not SPI.** The baro only needs tens of readings a second. Putting
  it on I2C1 keeps SPI1 for the gyro alone.
- **CSB is tied straight to 3.3 V.** If CSB ever sees a low edge, the BMP280
  switches to SPI mode until it's power-cycled. Hard-tying it high avoids
  that.
- **This block holds the I2C bus's only pull-ups (4.7k).** I2C1 also goes to
  the expansion header for add-on I2C sensors, such as a ToF board in the
  rear sensor bay. Add-on boards must not bring their own pull-ups, or the
  bus ends up with several sets in parallel.

## Placement and assembly

- **Prop wash:** air from the props changes the pressure the sensor sees,
  which shows up as altitude noise. Cover the sensor with a small piece of
  open-cell foam, as most flight controllers do. Don't seal the vent hole.
- **Heat:** keep it away from the buck-boost (U10), the LDOs and the motor
  FETs. Their heat drifts the temperature-compensated reading.
- **Gyro:** keep it away from the gyro too. The two don't interfere
  electrically, but both prefer the quiet middle of the board, so plan the
  placement together.

## To verify before layout

- [ ] Choose the BMP280's position with the foam cover in mind: it needs
      some free air above the vent and has to be reachable for the foam.
- [ ] Betaflight target: `BARO_I2C_INSTANCE` I2C1 with BMP280 at 0x76.
- [ ] Confirm the expansion header carries I2C1 without extra pull-ups.
