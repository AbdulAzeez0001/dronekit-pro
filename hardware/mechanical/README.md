# Mechanical — 1S brushed cage frame

Source design: Fusion, Default Project → **DroneKit Cage** (fully parametric;
edit sizes under Modify → Change Parameters).

## Frame at default parameters

- Motors: **720 brushed** (7 × 20 mm), 40 mm props, 85 mm wheelbase.
- Cage: top ring and struts over the props, about 108 × 108 × 34 mm (46 mm with the battery holder under the plate), about 10.3 g in PLA (1.0 mm rods, 1.5 mm rings, 1.5 mm motor-pod walls with a 10 mm grip, 3 mm arms, 2 mm battery holder).
- Top opening: the top is cut open over the square between the motor hubs (`2 × motor_offset` across, 60 mm at 85 mm wheelbase), with a rim rod around it. The props stay covered; the electronics are open from above.
- Props sit at z = 27–30 mm, 2.75 mm below the top struts, with 20 mm between neighbouring prop tips.
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
| Second board | **vision** board, same outline and holes, 1.0 mm, stacked at least 5.5 mm above fc on a 2 × 12 1.27 mm header + socket (`hardware/board/README.md`, "Two boards") |
| ESP32-S3 antenna | on the vision board's rear edge, ending 1.4 mm past it (x = −17.4 mm); keep cage parts and metal away from it |

### Size limits (from the cage, at default parameters)

- **X ≤ 34 mm** — camera cradle starts at x = +17 mm.
- **Y ≤ 31.8 mm** — the centre plate is 36 mm; the battery posts at y = ±16.6 mm now hang under the plate.
- **Above fc: open.** The battery hangs **under** the centre plate
  (changed 2026-11-26), so nothing sits over the boards: the two-board stack
  (5.5 mm gap + 1.0 mm vision board + 3.1 mm ESP32-S3 module = 9.6 mm, top
  at z = 16.8 mm) has the open top above it, and the props start 10 mm out
  to the side at z = 27 mm. `fc_clear` (11.7 mm) no longer drives anything.
- **Battery:** z = −10 to −2 mm, under the plate, in a holder of 2 mm
  rods (`bat_rod`): four posts, two rails across the battery top and
  bottom, and two side rails that close the bottom into a frame. `bat_z` =
  −(`bat_h` + `bat_rod`). It is 29 mm below the props, and the holder's
  bottom frame (z = −12 mm) is the drone's lowest point and takes the
  landings. Checked in Fusion with a stand-in for the vision board and
  module: no clash with the cage, props, camera, motors or battery, and the
  battery and holder are outside a 25° cone below the flow/ToF sensor.

### Strength (2026-11-26)

Made stronger after the first look: motor-pod walls and ribs 1.0 → 1.5 mm
(`pod_wall`), grip 8 → 10 mm (`pod_h`), arms 2.5 → 3 mm (`arm_w`), and the
battery holder 1.0 → 2.0 mm rods with a closed bottom frame. Cage mass
8.2 → 10.3 g. Not yet printed. PLA is stiff but brittle in a crash; PETG
or nylon is tougher for the same shape, at about the same weight
(PETG 1.27 g/cm³, nylon ~1.1).
- **Bottom-side parts:** 3.5 mm keep-out circles around each mounting hole
  (standoff bosses); otherwise ~3.5 mm of clearance to the cage plate.

### Layout notes

- Put the ESP32-S3 antenna at a board edge (the battery now hangs under
  the plate, lying along Y, below the fc board).
- Motor wires drop through the holder bases at the four corners
  (motors at x, y = ±26.5 mm) — put the four motor pads near the board corners.
- Camera 24-pin FPC connector (J30, Hirose FH12) on the **vision** board's underside at the +X edge, x = 8–16 mm, about 17 mm wide, 2 mm tall, opening toward the camera (the Fusion placeholder still shows it on fc's top from the one-board layout); ToF / optical-flow header toward −X.
- Battery lead comes from the side (±Y).

Verified in Fusion: the board does not touch the cage, and a 3 mm parts zone
above it is clear of the cage. Not yet printed or fit-tested.
