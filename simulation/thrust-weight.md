# Thrust-to-weight check — 1S brushed, 720 motors, 40 mm props

Date: 2026-11-23. Model: `thrust_weight.py` (run it to reproduce or try
changes). This is a first-order estimate. **The one number it can't pin down
is the 720 motor's thrust on a 40 mm prop, so a bench test of one motor
(below) is the next step.**

## Verdict

**With a 300 mAh pack the drone should fly as a docile whoop, a little
heavier than the Beta75.** The cage is fully covered (top ring and top
struts) on an 85 mm wheelbase, about 108 × 108 × 34 mm. The top is cut open over
the square between the motor hubs, with a 1 mm rim rod around the
opening, so the props stay covered while the electronics are open from
above. It weighs **8.2 g**. It started at 10.8 g on a 75 mm wheelbase.
Thinner parts (`rod_w` 1.4 → 1.0 mm, `ring_w` 2.0 → 1.5 mm, `pod_wall`
1.2 → 1.0 mm) brought it to 7.9 g. The wider wheelbase added 0.4 g, and
the centre opening with its rim took off 0.05 g. The quad
most like it that actually flew (BetaFPV's Beta75: same 7 × 20 mm motors,
40 mm props, 75 mm frame) weighed about **39 g** ready to fly. DroneKit
comes out at about **43 g** with a 300 mAh pack, or **48 g** with the
450 mAh pack. The wider wheelbase doesn't change the thrust model, because
the prop area is the same.

| Scenario | All-up weight | Thrust/weight (low–mid–high) | Hover current | Flight time |
|---|---|---|---|---|
| Current design (8.2 g cage, open centre), 450 mAh | 47.7 g | 1.5 – **1.8** – 2.1 | 3.6 A | ~4.5 min |
| Current design (8.2 g cage, open centre), 300 mAh | 43.3 g | 1.6 – **2.0** – 2.3 | 3.1 A | ~3.5 min |
| 0.8 mm PCB (−1.4 g), 300 mAh | 41.9 g | 1.7 – **2.0** – 2.4 | 2.9 A | ~3.6 min |
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
| Cage, PLA, covered with an open centre, 108 × 108 × 34 mm (85 mm wheelbase) | 8.2 | Fusion model volume (6.60 cm³) × 1.24 g/cm³ |
| 4 × 7×20 motors | 14.0 | BetaFPV 7×20 listing: ~3.5 g each (some generic 720s are up to ~5 g) |
| Flight controller (PCB 2.9 + ESP32-S3 module ~3 + parts ~2.5) | 8.4 | estimate |
| Props, camera, wiring, foam | 4.4 | estimate |
| **Dry** | **35.0** | |
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
the 1.6 mm PCB, the ESP32-S3 module and six connectors. That's the cost of
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
   found for a 720 on a 40 mm prop. The range is 6–10 W of electrical power
   per motor at full throttle (about 2–2.7 A at ~3.5 V), which gives 71–100 g
   of total thrust. That's the "low–mid–high" spread in the table.

**What the model leaves out:** the cage's ring around each prop isn't a
tight duct, so it's treated as open props. Some recirculation loss there is
possible, which would make things slightly worse.

## What to do about it

In order of impact:

1. **Lighten the cage.** The rods are now 1.0 mm, the rings 1.5 mm and
   the pod walls 1.0 mm. The top is open over the centre square and
   covered over the props, and the cage is 8.2 g on an 85 mm wheelbase.
   Removing the whole top would save roughly another 1.5 g (estimate), but it leaves
   the props unguarded at their own height.
2. **Fly a 300 mAh pack, not 450.** It's 4.4 g lighter. Flight time
   barely changes, because the drone hovers more efficiently.
3. **Use a 0.8 mm PCB instead of 1.6 mm.** It saves about 1.4 g, and whoop
   flight controllers normally use 0.8–1.0 mm. Check the stiffness against
   the four-screw mount.
4. **If that's not enough, step up the motors.** BetaFPV's own answer was
   the Beta75S with **8 × 20 mm motors** on the same 40 mm props. The cage's
   motor holders follow `motor_d`, so that's a parameter change (7 → 8 mm)
   plus a check on the motor FETs and flyback diodes for the higher
   current. The longer-term upgrade path, already noted in the pivot, is
   1S brushless (0802 + ESC), which is lighter and far more efficient.

## Next: bench-test one motor (replaces the guesswork)

You need one 720 motor, one 40 mm prop, a charged 1S pack, a kitchen scale
reading to 0.1 g, and a way to switch the motor on (a bench supply at 3.7 V
works too).

1. Fix the motor to a small block on the scale with the prop **blowing
   upward**, so thrust pushes the block down. Tare the scale.
2. Run it at full power. Read the grams and, if you can, the current.
3. Multiply by 4 for the total thrust, then divide by the all-up weight.

If one motor gives **at least ~25 g**, the current design can work, at a
thrust/weight of about 2. Below about 20 g, lighten the cage or move to
8 × 20 motors first.
