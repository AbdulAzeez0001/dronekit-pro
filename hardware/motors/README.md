# Motor driver block

Circuit as code. `motors.py` is the source of truth; `motors.net` is the
generated KiCad netlist. Design notes: `motor-design.md`.

## Regenerate
```
pip install skidl --break-system-packages
python3 motors.py           # runs ERC, writes motors.net
```
Expected: `ERC INFO: No errors or warnings` and `0 errors`.

## Use in KiCad
Don't import this netlist on its own. `hardware/board/build_board.py` merges
every block into one schematic, `hardware/board/board.kicad_sch`, with the real
STM32 and ESP32-S3 pin numbers. See `hardware/board/README.md`.

## What NOT to change without re-reading the design doc
- R44–R47 are gate pull-DOWNs. They keep the motors off while the STM32 boots.
- D40–D43 (flyback diodes) are not optional.
- Motor M+ pads sit on VBAT_RAW, not on the protected VBAT.
