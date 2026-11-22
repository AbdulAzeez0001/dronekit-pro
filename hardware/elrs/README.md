# RC receiver port (optional ELRS add-on)

The ELRS receiver is optional: the user buys a small serial ELRS receiver and
solders it to the four `J60` pads. This block is just that port.

Circuit as code. `elrs.py` is the source of truth; `elrs.net` is the
generated KiCad netlist. Design notes: `elrs-design.md`.

## Regenerate
```
pip install skidl --break-system-packages
python3 elrs.py             # runs ERC, writes elrs.net
```
Expected: `ERC INFO: No errors or warnings` and `0 errors`.

## Import into KiCad
Same as the other blocks: File > Import > Netlist, then assign real symbols.
`U1` here is the same STM32F405 as `U1` in the dual-boot netlist, so merge
them into one part in the full schematic.

## What NOT to change without re-reading the design doc
- Pad order (GND, PWR, FC_TX, FC_RX) matches common receivers' wire order.
- Keep the 100R series resistors on the UART lines.
- PWR is +3V8 because the board has no 5V; check a receiver's input range
  before recommending it.
