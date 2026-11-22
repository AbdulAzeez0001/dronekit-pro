# Buzzer block

Circuit as code. `buzzer.py` is the source of truth; `buzzer.net` is the
generated KiCad netlist. Design notes: `buzzer-design.md`.

## Regenerate
```
pip install skidl --break-system-packages
python3 buzzer.py           # runs ERC, writes buzzer.net
```
Expected: `ERC INFO: No errors or warnings` and `0 errors`.

## Import into KiCad
Same as the other blocks. `U1` here is a stub of the STM32 (PB8 only); keep
the `hardware/stm32` block's `U1` and let the `BEEPER` net join by name.

## What NOT to change without re-reading the design doc
- BZ+ is on +3V8, not VBAT (2S would over-volt a 5V buzzer) and not +3V3_SYS.
- R121 gate pull-down keeps it silent while the STM32 boots.
- D120 flyback diode stays (magnetic buzzers are inductive).
