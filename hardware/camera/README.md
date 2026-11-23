# Camera block

Circuit as code. `camera.py` is the source of truth; `camera.net` is the
generated KiCad netlist. Design notes: `camera-design.md`.

## Regenerate
```
pip install skidl --break-system-packages
python3 camera.py           # runs ERC, writes camera.net
```
Expected: `ERC INFO: No errors or warnings` and `0 errors`.

## Use in KiCad
Don't import this netlist on its own. `hardware/board/build_board.py` merges
every block into one schematic, `hardware/board/board.kicad_sch`, with the real
STM32 and ESP32-S3 pin numbers. See `hardware/board/README.md`.

## What NOT to change without re-reading the design doc
- `R30` pulls CAM_PWDN UP. That keeps the camera powered down whenever the
  ESP32-S3 is off (Mode A). Don't tie PWDN low.
- The camera rails come from `+3V3_ESP`, never `+3V3_SYS` (gyro rail).
- Check the FPC connector's pin-1 side against the module before layout;
  two numbering conventions exist for this connector.
