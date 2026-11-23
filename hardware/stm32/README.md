# STM32F405 block

Circuit as code. `stm32.py` is the source of truth; `stm32.net` is the
generated KiCad netlist. Design notes: `stm32-design.md`.

This block defines `U1` (STM32F405RGT6) with all 64 real LQFP64 pin numbers
and ties each pin other blocks use to that block's net name. It is the master
pin definition for the board.

## Regenerate
```
pip install skidl --break-system-packages
python3 stm32.py            # runs ERC, writes stm32.net
```
Expected: `ERC INFO: No errors or warnings` and `0 errors`.

## Use in KiCad
Don't import this netlist on its own. `hardware/board/build_board.py` merges
every block into one schematic, `hardware/board/board.kicad_sch`, with the real
STM32 and ESP32-S3 pin numbers. See `hardware/board/README.md`.

## What NOT to change without re-reading the design doc
- VCAP_1 / VCAP_2 need 2.2 uF each (ESR < 2 ohm).
- VBUS powers the logic only through the power block's USB path; never wire it
  straight to VBAT or VBAT_RAW (that would back-feed the LiPo).
- The BOOT button's 1k protects the ESP32-S3 pin that also drives BOOT0.
