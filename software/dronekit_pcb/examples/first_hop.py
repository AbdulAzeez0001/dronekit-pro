"""A first hop: arm, lift off gently, hover, land.

    python first_hop.py          # on the simulator
    python first_hop.py --real   # on a real drone (join its Wi-Fi first)

On a real drone: clear space, props on only when you're ready, and start
with a low throttle. There's no altitude hold, so the right hover throttle
depends on your battery and motors. Raise HOVER a little at a time.
"""

import sys

from dronekit_pcb import ArmError, Drone, DroneError
from dronekit_pcb.sim import SimDrone

HOVER = 0.45        # throttle 0..1
MAX_THROTTLE = 0.6  # this program can't go above this


def fly(drone: Drone) -> None:
    print(f"battery {drone.battery:.2f} V")
    try:
        drone.arm()
    except ArmError as e:
        print("won't arm:", e)
        return
    drone.takeoff(throttle=HOVER, ramp=1.0)
    drone.hover(2.0)
    drone.land(seconds=1.5)
    print("landed")


def main() -> None:
    try:
        if "--real" in sys.argv:
            with Drone("192.168.4.1", max_throttle=MAX_THROTTLE) as drone:
                drone.wait_for(lambda t: t.vbat > 0, 2)
                fly(drone)
        else:
            with SimDrone() as sim, Drone(None, transport=sim.connect(),
                                          max_throttle=MAX_THROTTLE) as drone:
                drone.wait_for(lambda t: t.vbat > 0, 2)
                fly(drone)
                print(f"simulated peak height {sim.max_altitude:.2f} m (toy model)")
    except DroneError as e:
        print("stopped:", e)


if __name__ == "__main__":
    main()
