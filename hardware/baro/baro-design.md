# Barometer — Goertek SPA06-003 on I2C1

Status: decided (2026-11-23), ERC clean (`baro.py` → `baro.net`). Not yet
laid out.

**Changed from the BMP280.** LCSC lists the BMP280 as discontinued, with 0–2
in stock at about $10.6. The SPA06-003 is about $0.43 with tens of thousands
in stock (see `docs/bom-cost.md`). Betaflight reads it with its DPS310
driver, which covers the DPS310, DPS368, SPL07-003 and SPA06-003. The
SPA06-003's pinout matches the BMP280's pin for pin, so the swap changes the
part, its value and the pull-ups, but no wiring.

## What it's for

- **Mode A (Fly):** Betaflight uses the baro for altitude in the OSD and
  logs, and for its altitude features.
- **Mode B (Code):** the ESP32-S3 can read altitude from the STM32 over MSP,
  which gives student code a "hold this height" building block.

## Circuit

| SPA06-003 pin | Connects to | Why |
|---|---|---|
| 8 VDD, 6 VDDIO | +3V3_SYS, 100 nF each at the pins | clean rail; pressure readings pick up supply noise |
| 1, 7 GND | GND | |
| 4 SCK | STM32 PB6 (I2C1_SCL), 5.1k pull-up | |
| 3 SDA | STM32 PB7 (I2C1_SDA), 5.1k pull-up | |
| 2 CSB | +3V3_SYS (VDDIO) | I2C mode |
| 5 SDO | GND | address 0x76 |

Values are from the Goertek SPA06-003 datasheet (Ver 2.0, 2023-12-05):

- **Pinout and CSB:** Table 11 gives the 8-pin LGA (2.0 × 2.5 × 0.95 mm)
  pinout. In I2C mode, CSB is left open or tied to VDDIO.
- **Address:** 0x77 by default, or 0x76 with SDO pulled to GND.
- **Parts:** Table 6 gives pull-ups of 5k–100k, and supply capacitors of
  100 nF "as close to the package pins as possible".
- **Supply range:** VDD 1.7–3.6 V, VDDIO 1.08–3.6 V.

## Design choices

- **I2C, not SPI.** The baro only needs tens of readings a second. Putting
  it on I2C1 keeps SPI1 for the gyro alone.
- **CSB tied to VDDIO.** Table 11 allows open or VDDIO. Tying it means the
  part can never fall into SPI mode.
- **5.1k pull-ups (not 4.7k).** Table 6's minimum is 5k, so the old BMP280
  design's 4.7k was just under it. 5.1k is also the value the USB-C CC
  resistors use, which saves a BOM line.
- **This block holds the I2C bus's only pull-ups.** I2C1 also goes to the
  SENSOR expansion header (J130). Add-on boards must not bring their own
  pull-ups, or the bus ends up with several sets in parallel.

## Placement and assembly

- **Prop wash:** air from the props changes the pressure the sensor sees,
  which shows up as altitude noise. Cover it with a small piece of open-cell
  foam, as most flight controllers do. Don't seal the vent hole.
- **Heat:** keep it away from the buck-boost (U10), the LDOs and the motor
  FETs. Their heat drifts the temperature-compensated reading.
- **Gyro:** keep it away from the gyro too. They don't interfere, but both
  prefer the quiet middle of the board, so plan the placement together.

## To verify before layout

- [ ] Check the footprint: it's the same 2.0 × 2.5 mm, 0.65 mm-pitch LGA-8
      as the BMP280, but check the land pattern against Goertek's outline
      drawing (datasheet section 8.2).
- [x] Betaflight target: `BARO_I2C_INSTANCE` I2C1, baro hardware DPS310
      (`firmware/betaflight/config/DRONEKITPRO/config.h`).
      `baro_i2c_address` = 118 (0x76) is set in `cli-defaults.txt`.
- [ ] Confirm the Betaflight version in use includes the DPS310 driver.
      From 4.5, only the baro drivers built into the firmware are available.
- [ ] Place it with the foam cover in mind: free air above the vent, and
      reachable for the foam.
