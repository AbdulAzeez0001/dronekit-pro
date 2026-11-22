# Gyro block (ICM-42688-P)

Circuit as code. `gyro.py` is the source of truth; `gyro.net` is the
generated KiCad netlist. Design notes: `gyro-design.md`.

## Regenerate
```
pip install skidl --break-system-packages
python3 gyro.py             # runs ERC, writes gyro.net
```
Expected: `ERC INFO: No errors or warnings` and `0 errors`.

## Import into KiCad
Same as the other blocks: File > Import > Netlist, then assign real symbols.
`U1` here is the same STM32F405 as `U1` in the dual-boot netlist, so merge
them into one part in the full schematic.

## What NOT to change without re-reading the design doc
- The IMU stays on +3V3_SYS, never +3V3_ESP or +3V8.
- Pin 7 (RESV) must stay on GND; pin 9 (INT2/FSYNC) is grounded because FSYNC is unused.
- LGA package: machine assembly only (not hand-solderable).
