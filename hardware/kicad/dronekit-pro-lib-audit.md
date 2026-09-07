# Custom symbol audit — `dronekit-pro-lib.kicad_sym`

Pin-by-pin check of the two project-local symbols against their datasheets
(number, name, electrical type). Done 2026-09-07.

Datasheets:
- MP2307: Monolithic Power Systems MP2307 Rev. 1.9 (5/28/2008), "PIN FUNCTIONS" p.5.
- RT9013: Richtek RT9013 DS9013-10 (April 2011), "Functional Pin Description",
  SOT-23-5 / SC-70-5 column.

## MP2307DN — package SOIC-8-EP (KiCad `SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.29x3mm`, pads 1-9)

| Pin | Datasheet name | Datasheet function              | Symbol name | Symbol type | Status |
|-----|----------------|---------------------------------|-------------|-------------|--------|
| 1   | BS             | High-side gate-drive boost in   | BS          | passive     | fixed (was "BST" / input) |
| 2   | IN             | Power input, 4.75-23 V          | IN          | power_in    | OK     |
| 3   | SW             | Power switching output          | SW          | passive     | fixed (was output) |
| 4   | GND            | Ground (tie EP to pin 4)        | GND         | power_in    | OK     |
| 5   | FB             | Feedback input, 0.925 V thresh  | FB          | input       | OK     |
| 6   | COMP           | Compensation node (ext RC->GND) | COMP        | passive     | fixed (was output) |
| 7   | EN             | Enable input (digital)          | EN          | input       | OK     |
| 8   | SS             | Soft-start control input        | SS          | passive     | fixed earlier (was "NC" / no_connect) |
| 9   | (EP)           | Exposed pad = pin 4 (GND)       | EP          | power_in    | OK — maps to footprint pad 9, tied to GND |

Notes:
- Pin 1: datasheet uses "BS"; the schematic net on this node is still named
  "BST" (net names are arbitrary; not changed).
- Pin-type changes (BS/SW/COMP -> passive) are KiCad-convention cleanups; no
  ERC or functional effect (their nets are cap/RC nodes).

## RT9013-33 — package SOT-23-5 (KiCad `Package_TO_SOT_SMD:SOT-23-5`, 5 pads, no EP)

| Pin | Datasheet name | Datasheet function            | Symbol name | Symbol type | Status |
|-----|----------------|-------------------------------|-------------|-------------|--------|
| 1   | VIN            | Supply input                  | VIN         | power_in    | OK     |
| 2   | GND            | Common ground                 | GND         | power_in    | OK     |
| 3   | EN             | Enable input, active high     | EN          | input       | OK     |
| 4   | NC             | No internal connection        | NC          | no_connect  | OK     |
| 5   | VOUT           | Regulator output              | VOUT        | power_out   | OK     |

RT9013-33: no mismatches. SOT-23-5 has no exposed pad; symbol correctly has none.

## Result

- RT9013-33: correct as-is.
- MP2307DN: pin 8 was mislabeled NC (fixed, commit 1051494); pin 1 name
  BST->BS and BS/SW/COMP electrical types -> passive (this change). All pin
  numbers and names now match the datasheet.
