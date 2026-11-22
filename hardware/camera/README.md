# Camera block

Circuit as code. `camera.py` is the source of truth; `camera.net` is the
generated KiCad netlist. Design notes: `camera-design.md`.

## Regenerate
```
pip install skidl --break-system-packages
python3 camera.py           # runs ERC, writes camera.net
```
Expected: `ERC INFO: No errors or warnings` and `0 errors`.

## Import into KiCad
Same as `hardware/dual-boot/`: File > Import > Netlist, then assign real
symbols. `U2` here is the same ESP32-S3 as `U2` in the dual-boot netlist
(camera pins only), so merge them into one part in the full schematic.

## What NOT to change without re-reading the design doc
- `R30` pulls CAM_PWDN UP. That keeps the camera powered down whenever the
  ESP32-S3 is off (Mode A). Don't tie PWDN low.
- The camera rails come from `+3V3_ESP`, never `+3V3_SYS` (gyro rail).
- Check the FPC connector's pin-1 side against the module before layout;
  two numbering conventions exist for this connector.
