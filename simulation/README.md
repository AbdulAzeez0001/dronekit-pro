# Simulation (MIT)

Free, no-hardware validation. Order of value:

1. eCalc (xcopterCalc) inputs - airframe thrust-to-weight and flight time.
   Run this FIRST; it tells you if the drone flies before you buy a motor.
2. Lightweight Python rigid-body sim - validates the dronekit_pcb command
   API (takeoff, move_forward, the 2m square). NOT full aero physics.
3. Betaflight SITL notes - Mode A logic without a board.

Do not reach for Gazebo/PX4: wrong stack (you are on Betaflight + ESP32).

## Done so far
- `thrust_weight.py` + `thrust-weight.md` — first-order thrust-to-weight and
  flight-time estimate for the 1S brushed design, calibrated on the BetaFPV
  Beta75 (7x20 motors / 40 mm props / 75 mm frame). Verdict: heavier than
  the Beta75 (46.6 g with 300 mAh vs its ~39 g), with a 10.3 g cage on an
  85 mm wheelbase; 8x20 motors (2026-11-26) bring mid thrust/weight to 2.0; next step is a one-motor bench test.
