# Mechanical — 1S brushed cage frame

Source design: Fusion, Default Project → **DroneKit Cage** (fully parametric;
edit sizes under Modify → Change Parameters).

## Frame at default parameters

- Motors: **720 brushed** (7 × 20 mm), 40 mm props, 75 mm wheelbase.
- Cage: about 101 × 101 × 34 mm, about 11 g in PLA.
- Props sit at z = 27–30 mm, 2.3 mm below the top struts.
- For 716 motors, set `motor_len` = 16 and `cage_h` = 30.

## Flight-controller PCB that fits the cage

`fc_pcb_outline.dxf` — board edge + mounting holes, in mm, origin at board
centre. Import into KiCad as **Edge.Cuts** (File → Import → Graphics, units mm).

| | |
|---|---|
| Board | 32 × 30 mm (X × Y), 1.6 mm thick, 2 mm corner radius |
| Mounting holes | 4 × Ø1.6 mm (M1.4) on a 25.5 mm square, centred |
| Orientation | +X = front (camera side), −X = rear (sensor bay) |
| Board sits at | 5.6 mm above cage floor (on 4 mm standoffs) |

### Size limits (from the cage, at default parameters)

- **X ≤ 34 mm** — camera cradle starts at x = +17 mm.
- **Y ≤ 31.8 mm** — battery-cage posts at y = ±16.6 mm.
- **Top-side parts ≤ 4.4 mm tall** — the battery underside sits 4.4 mm above
  the board (ESP32-S3-WROOM-1 at 3.1 mm fits; raise `fc_clear` for taller parts).
- **Bottom-side parts:** 3.5 mm keep-out circles around each mounting hole
  (standoff bosses); otherwise ~3.5 mm of clearance to the cage plate.

### Layout notes

- Put the ESP32-S3 antenna at a board edge, not under the battery
  (battery sits above the board, lying along Y).
- Motor wires drop through the holder bases at the four corners
  (motors at x, y = ±26.5 mm) — put the four motor pads near the board corners.
- Camera 24-pin FPC connector (J30) on top at the +X edge, x = 11.5–15.5 mm, 16 mm wide, 2 mm tall (placeholder in Fusion); ToF / optical-flow header toward −X.
- Battery lead comes from the side (±Y).

Verified in Fusion: the board does not touch the cage, and a 3 mm parts zone
above it is clear of the cage. Not yet printed or fit-tested.
