# Expansion headers block

Circuit as code. `expansion.py` is the source of truth; `expansion.net` is
the generated KiCad netlist. Design notes: `expansion-design.md`.

Six JST-SH headers: SENSOR (I2C1), UART3, LED, PWM on the STM32; CODE-I2C and
CODE-IO on the ESP32-S3.

## Regenerate
```
pip install skidl --break-system-packages
python3 expansion.py        # runs ERC, writes expansion.net
```
Expected: `ERC INFO: No errors or warnings` and `0 errors`.

## Use in KiCad
Don't import this netlist on its own. `hardware/board/build_board.py` merges
every block into one schematic, `hardware/board/board.kicad_sch`, with the real
STM32 and ESP32-S3 pin numbers. See `hardware/board/README.md`.

## What NOT to change without re-reading the design doc
- Header 3V3 is `+3V3_ESP`, never `+3V3_SYS` (gyro rail).
- Both I2C headers keep the Qwiic pin order: GND, 3V3, SDA, SCL.
- Don't add pull-ups for J130; I2C1's pull-ups are in the baro block.
