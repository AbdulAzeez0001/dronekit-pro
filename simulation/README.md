# Simulation (MIT)

Free, no-hardware validation. Order of value:

1. eCalc (xcopterCalc) inputs - airframe thrust-to-weight and flight time.
   Run this FIRST; it tells you if the drone flies before you buy a motor.
2. Lightweight Python rigid-body sim - validates the dronekit_pcb command
   API (takeoff, move_forward, the 2m square). NOT full aero physics.
3. Betaflight SITL notes - Mode A logic without a board.

Do not reach for Gazebo/PX4: wrong stack (you are on Betaflight + ESP32).
