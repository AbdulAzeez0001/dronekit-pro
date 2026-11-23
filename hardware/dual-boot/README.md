# Dual-boot control subcircuit

Circuit as code. `dual_boot.py` is the source of truth; `dual_boot.net` is the
generated KiCad netlist.

## Regenerate
```
pip install skidl --break-system-packages
python3 dual_boot.py        # runs ERC, writes dual_boot.net
```
Expected: `ERC INFO: No errors or warnings` and `0 errors`.

## Use in KiCad
Don't import this netlist on its own. `hardware/board/build_board.py` merges
every block into one schematic, `hardware/board/board.kicad_sch`, with the real
STM32 and ESP32-S3 pin numbers. See `hardware/board/README.md`.

## What NOT to change without re-reading the design doc
- `r_en` is a pull-DOWN on ESP_EN. This is the fail-safe (ESP32-S3 dark by
  default). Do not "fix" it to a pull-up.
- The STM32 connects only to EN, the UART bridge, and the two flash-control
  lines. Nothing on STRAP_IO0/45/46. STRAP_IO45 high at boot selects 1.8V
  flash/PSRAM and the S3 will not boot.
