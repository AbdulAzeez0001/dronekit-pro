# Motor driver block

Circuit as code. `motors.py` is the source of truth; `motors.net` is the
generated KiCad netlist. Design notes: `motor-design.md`.

## Regenerate
```
pip install skidl --break-system-packages
python3 motors.py           # runs ERC, writes motors.net
```
Expected: `ERC INFO: No errors or warnings` and `0 errors`.

## Import into KiCad
Same as the other blocks: File > Import > Netlist, then assign real symbols.
`U1` here is the same STM32F405 as `U1` in the dual-boot netlist (motor pins
only), so merge them into one part in the full schematic.

## What NOT to change without re-reading the design doc
- R44–R47 are gate pull-DOWNs. They keep the motors off while the STM32 boots.
- D40–D43 (flyback diodes) are not optional.
- Motor M+ pads sit on VBAT_RAW, not on the protected VBAT.
