# Thrust-to-weight check — 1S brushed, 8×20 motors, 40 mm props

Date: 2026-11-23; motors changed to 8×20 on 2026-11-26. Model: `thrust_weight.py` (run it to reproduce or try
changes). This is a first-order estimate. **The one number it can't pin down
is the 8×20 motor's thrust on a 40 mm prop, so a bench test of one motor
(below) is the next step.**

## Verdict

**With 8×20 motors and a 300 mAh pack the drone should fly as a docile
whoop (mid thrust/weight 2.0), heavier than the Beta75.** The cage is fully covered (top ring and top
struts) on an 85 mm wheelbase, about 108 × 108 × 34 mm, with the battery under the centre plate. The top is cut open over
the square between the motor hubs, with a 1 mm rim rod around the
opening, so the props stay covered while the electronics are open from
above. It weighs **10.3 g** since the motor pods, arms and battery holder
were made stronger (2026-11-26: +2.1 g; it was 8.2 g). It started at 10.8 g on a 75 mm wheelbase.
Thinner parts (`rod_w` 1.4 → 1.0 mm, `ring_w` 2.0 → 1.5 mm, `pod_wall`
1.2 → 1.0 mm) brought it to 7.9 g. The wider wheelbase added 0.4 g, and
the centre opening with its rim took off 0.05 g. The quad
most like it that actually flew (BetaFPV's Beta75: 7 × 20 mm motors,
40 mm props, 75 mm frame) weighed about **39 g** ready to fly. DroneKit
comes out at about **46.6 g** with a 300 mAh pack, or **51 g** with the
450 mAh pack. That includes the second board of the two-board electronics
stack (2026-11-23, see `hardware/board/README.md`), which added about 3 g:
the 1.0 mm vision PCB and the board-to-board header pair and standoffs.
The battery hangs under the centre plate, so the cage didn't need to grow
taller for the stack. The wider wheelbase doesn't change the thrust model, because
the prop area is the same.

| Scenario | All-up weight | Thrust/weight (low–mid–high) | Hover current | Flight time |
|---|---|---|---|---|
| Current design (8×20, 0.8 mm fc), 450 mAh | 51.0 g | 1.5 – **1.8** – 2.1 | 4.0 A | ~4.1 min |
| Current design (8×20, 0.8 mm fc), 300 mAh | 46.6 g | 1.7 – **2.0** – 2.3 | 3.5 A | ~3.1 min |
| 1.6 mm fc PCB instead (+1.4 g), 300 mAh | 48.0 g | 1.6 – **1.9** – 2.2 | 3.6 A | ~3.0 min |
| 7×20 motors instead (before 2026-11-26), 300 mAh | 46.6 g | 1.5 – **1.8** – 2.1 | 3.5 A | ~3.1 min |
| BetaFPV Beta75 (reference, flew) | 39.0 g | 1.8 – 2.2 – 2.6 | 2.6 A | 3.5 min (stated) |

**How to read thrust/weight:**

- **Below about 1.5:** it barely flies, and battery sag soon makes it worse.
- **About 2:** a docile indoor whoop that's fine for beginners. That's
  roughly where the Beta75 sat.
- **2.5 and up:** lively.

**Battery sag:** under load a 1S cell drops from 4.2 V toward 3.3 V, which
cuts brushed-motor thrust by roughly a quarter late in the pack. So a
thrust/weight of 1.8 when fresh feels like about 1.3 near the end of a
flight.

## Where the weight is

| Item | g | Source |
|---|---|---|
| Cage, PLA, covered with an open centre, 108 × 108 × 34 mm, battery holder under the plate, 8 mm motor pods with 1.5 mm walls, 3 mm arms (85 mm wheelbase) | 10.3 | Fusion model volume (8.29 cm³) × 1.24 g/cm³ |
| 4 × 8×20 motors | 14.0 | BetaFPV 8×20 15000 KV listing: ~3.5 g each |
| Flight controller (0.8 mm PCB 1.5 + ESP32-S3 module ~3 + parts ~2.5) | 7.0 | estimate |
| Second board: vision PCB 1.0 mm (1.8) + header pair and standoffs (0.8) | 2.6 | estimate |
| Props, camera, wiring, foam | 4.4 | estimate |
| **Dry** | **38.3** | |
| Battery: 450 mAh / 300 mAh | 12.7 / 8.3 | BetaFPV BT2.0 listings |

**The cage was the biggest thing to cut.** Moulded whoop frames are a few
grams; this printed cage started at about 10.8 g. Thinning the rods, rings
and motor-pod walls to 1.0–1.5 mm brought it to 7.9 g (75 mm wheelbase).
Widening to 85 mm and opening the top centre leave it at 8.2 g. At 75 mm, the 6.35 cm³ sat roughly
like this: top and bottom rings 0.8 cm³ each, the centre plate 1.36 cm³,
the four corner groups (arm, spokes, motor pod, standoff, post, top struts)
about 2.3 cm³, the sensor bay 0.35 cm³, the camera cradle 0.37 cm³ and the
battery cage 0.14 cm³.

**The flight controller** is heavier than a typical whoop board, because of
the ESP32-S3 module and six connectors (the fc PCB is 0.8 mm since 2026-11-26). That's the cost of
the dual-boot and expansion features.

## How the model works

1. **Hover power from momentum theory.** P = T^1.5 / √(2ρA), with four
   40 mm open props, divided by an overall efficiency of 0.22. That figure
   comes from bench tests of tiny brushed whoop motors, about 0.22–0.24
   total for 16.4–17.5k kV motors on 30 mm props
   ([mshtools, 2018](https://mshtools.wordpress.com/2018/01/23/tiny-whoop-efficiency-or-why-cannot-we-fly-long/)).
2. **Calibrated against a real quad.** The ideal flight time is scaled by
   0.74 so the model reproduces the Beta75: 32 g dry plus a 260 mAh pack,
   3 min 30 s stated
   ([BetaFPV Beta75](https://betafpv.com/products/beta75-bnf-tiny-whoop-quadcopter),
   [7×20 17500 kV motors](https://betafpv.com/products/7x20mm-coreless-brushed-motors-for-beta75)).
3. **Maximum thrust is a range,** because no published thrust figure was
   found for these motors on a 40 mm prop. For the 8×20 the range is
   7–11 W of electrical power per motor at full throttle (about 2–3.1 A at
   ~3.5 V), which gives 79–106 g of total thrust. The 7×20 range was 6–10 W
   (71–100 g). The 8×20 range is an estimate: a bigger can holds its speed
   better under load, which is why BetaFPV moved the Beta75 to 8×20
   (Beta75S). That's the "low–mid–high" spread in the table.

**What the model leaves out:** the cage's ring around each prop isn't a
tight duct, so it's treated as open props. Some recirculation loss there is
possible, which would make things slightly worse.

## What to do about it

In order of impact:

1. **Lighten the cage.** The rods are 1.0 mm and the rings 1.5 mm; the
   motor pods (1.5 mm), arms (3 mm) and battery holder (2 mm) were made
   thicker for strength, so the cage is 10.3 g on an 85 mm wheelbase.
   Of the +2.1 g: pod walls 0.8 g, battery holder 0.8 g, arms 0.55 g.
   Removing the whole top would save roughly another 1.5 g (estimate), but it leaves
   the props unguarded at their own height.
2. **Fly a 300 mAh pack, not 450.** It's 4.4 g lighter. Flight time
   barely changes, because the drone hovers more efficiently.
3. **Use a 0.8 mm PCB instead of 1.6 mm. Done (2026-11-26):** it saves
   about 1.4 g (mid thrust/weight 1.79 → 1.85), and whoop flight controllers
   normally use 0.8–1.0 mm. Check the stiffness against the four-screw mount
   on the first board.
4. **Step up the motors. Done (2026-11-26):** 8 × 20 mm motors, like
   BetaFPV's Beta75S, on the same 40 mm props. The cage's `motor_d` went
   7 → 8 mm and the flyback diodes SS34 (3 A) → SS54 (5 A, same footprint);
   mid thrust/weight 1.8 → 2.0 (estimate). The longer-term upgrade path, already noted in the pivot, is
   1S brushless (0802 + ESC), which is lighter and far more efficient.

## Next: bench-test one motor (replaces the guesswork)

You need one 8×20 motor, one 40 mm prop, a charged 1S pack, a kitchen scale
reading to 0.1 g, and a way to switch the motor on (a bench supply at 3.7 V
works too).

1. Fix the motor to a small block on the scale with the prop **blowing
   upward**, so thrust pushes the block down. Tare the scale.
2. Run it at full power. Read the grams and, if you can, the current.
3. Multiply by 4 for the total thrust, then divide by the all-up weight.

If one motor gives **at least ~25 g**, the current design works, at a
thrust/weight of about 2. Below about 20 g, lighten the cage first; past
that, the next step is 1S brushless.
