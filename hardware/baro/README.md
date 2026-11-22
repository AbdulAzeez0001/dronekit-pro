# Barometer block (BMP280)

Circuit as code. `baro.py` is the source of truth; `baro.net` is the
generated KiCad netlist. Design notes: `baro-design.md`.

## Regenerate
```
pip install skidl --break-system-packages
python3 baro.py             # runs ERC, writes baro.net
```
Expected: `ERC INFO: No errors or warnings` and `0 errors`.

## Import into KiCad
Same as the other blocks: File > Import > Netlist, then assign real symbols.
`U1` here is the same STM32F405 as `U1` in the dual-boot netlist, so merge
them into one part in the full schematic.

## What NOT to change without re-reading the design doc
- CSB stays tied to +3V3_SYS (a low edge locks the BMP280 into SPI mode).
- SDO stays on GND (address 0x76, Betaflight's default).
- R70/R71 are the I2C1 bus's only pull-ups.
