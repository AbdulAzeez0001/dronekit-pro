"""dronekit_pcb: program a DroneKit Pro in Code mode, from Python.

    from dronekit_pcb import Drone

    with Drone("192.168.4.1") as drone:
        drone.arm()
        drone.takeoff(throttle=0.45)
        drone.hover(2)
        drone.land()

Try programs first on the simulator: ``dronekit_pcb.sim.SimDrone``.
"""

from .drone import API_VERSION, Drone, Sticks, Telemetry
from .errors import ArmError, Disarmed, DroneError, LinkLost, NotPilot, arming_disable_names

__version__ = "0.1.0"

__all__ = [
    "API_VERSION", "Drone", "Sticks", "Telemetry",
    "ArmError", "Disarmed", "DroneError", "LinkLost", "NotPilot", "arming_disable_names",
]
