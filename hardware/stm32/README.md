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

## Merging the blocks in KiCad
Import every block's netlist into one schematic. Keep THIS block's `U1`
(real pin numbers); the `U1` in the dual-boot, gyro, baro, receiver and motor
netlists is a stub with local pin numbers, so delete it and let the nets join
by name (MODE_SENSE, GYRO_CS, M1_PWM, ...).

## What NOT to change without re-reading the design doc
- VCAP_1 / VCAP_2 need 2.2 uF each (ESR < 2 ohm).
- VBUS powers the logic only through the power block's USB path; never wire it
  straight to VBAT or VBAT_RAW (that would back-feed the LiPo).
- The BOOT button's 1k protects the ESP32-S3 pin that also drives BOOT0.
