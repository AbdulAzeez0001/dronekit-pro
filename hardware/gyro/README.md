# Gyro block (ICM-42688-P)

Circuit as code. `gyro.py` is the source of truth; `gyro.net` is the
generated KiCad netlist. Design notes: `gyro-design.md`.

## Regenerate
```
pip install skidl --break-system-packages
python3 gyro.py             # runs ERC, writes gyro.net
```
Expected: `ERC INFO: No errors or warnings` and `0 errors`.

## Use in KiCad
Don't import this netlist on its own. `hardware/board/build_board.py` merges
every block into one schematic, `hardware/board/board.kicad_sch`, with the real
STM32 and ESP32-S3 pin numbers. See `hardware/board/README.md`.

## What NOT to change without re-reading the design doc
- The IMU stays on +3V3_SYS, never +3V3_ESP or +3V8.
- Pin 7 (RESV) must stay on GND; pin 9 (INT2/FSYNC) is grounded because FSYNC is unused.
- LGA package: machine assembly only (not hand-solderable).
