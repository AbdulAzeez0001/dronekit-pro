# Dual-boot control subcircuit

Circuit as code. `dual_boot.py` is the source of truth; `dual_boot.net` is the
generated KiCad netlist.

## Regenerate
```
pip install skidl --break-system-packages
python3 dual_boot.py        # runs ERC, writes dual_boot.net
```
Expected: `ERC INFO: No errors or warnings` and `0 errors`.

## Import into KiCad
1. New project, open the schematic editor.
2. File > Import > Netlist, choose `dual_boot.net`.
3. Place the parts, then assign the real symbols. The netlist already carries
   proposed footprints; verify each against the BOM in `dual-boot-design.md`.
4. The two ICs (U1 STM32F405, U2 ESP32-WROOM-32) use minimal pin sets here -
   only the dual-boot nets. Add the remaining pins when you merge this into
   the full board schematic.

## What NOT to change without re-reading the design doc
- `r_en` is a pull-DOWN on ESP_EN. This is the fail-safe (ESP32 dark by
  default). Do not "fix" it to a pull-up.
- The STM32 connects only to EN, the UART2 bridge, and the two flash-control
  lines. Nothing on STRAP_IO0/2/12/15. STRAP_IO12 high at boot bricks the ESP32.
