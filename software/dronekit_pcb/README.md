# dronekit_pcb (MIT)

Program a DroneKit Pro in **Code mode** from Python. It talks to the
ESP32-S3 firmware's WebSocket API v1 (`firmware/esp32/src/api.h`).

```python
from dronekit_pcb import Drone

with Drone("192.168.4.1", max_throttle=0.6) as drone:
    drone.arm()
    drone.takeoff(throttle=0.45)
    drone.move(pitch=0.2, seconds=1)   # lean forward for 1 s
    drone.hover(2)
    drone.land()
```

Leaving the `with` block in any way (the end, an error, Ctrl+C) disarms
the drone.

## Install

```
pip install ./software/dronekit_pcb       # from the repo root
```

It needs Python 3.9+ and `websockets` (installed with it). The simulator
and the tests need nothing extra.

## Try it on the simulator first

```python
from dronekit_pcb import Drone
from dronekit_pcb.sim import SimDrone

with SimDrone() as sim, Drone(None, transport=sim.connect()) as drone:
    drone.arm()
    drone.takeoff(0.5)
    drone.hover(2)
    drone.land()
    print(sim.max_altitude)
```

`SimDrone` follows the same rules as the firmware: one pilot, the 0.5 s
timeout, arming only at low throttle, kill from anyone. Its altitude is a
toy model, for printing only. `examples/first_hop.py` runs on the
simulator, or on a real drone with `--real`.

## The commands

| Call | What it does |
|---|---|
| `Drone(host, max_throttle=0.7)` | Connect. Watching only, until you arm. |
| `arm()` | Become the pilot and arm. Raises `ArmError` with the reason, for example Betaflight's blocking checks by name (`THROTTLE`, `ARMSWITCH`...). |
| `takeoff(throttle, ramp)` | Ramp the throttle up from 0. **Open loop**: there's no altitude hold yet. |
| `hover(seconds)` | Keep the throttle, sticks centred. |
| `move(roll, pitch, yaw, seconds)` | Hold the sticks (-1..1), then centre them. |
| `land(seconds)` | Ramp the throttle down, then disarm. |
| `disarm()` | Stop the motors. |
| `kill()` | Stop now and give up being pilot. Any connection can do this. |
| `set_sticks(Sticks(...))` | Low level: set the sticks directly. |
| `telemetry`, `armed`, `battery` | The latest report (10 Hz). |
| `wait_for(condition, timeout)` | Wait until `condition(telemetry)` is true. |

Errors: `ArmError`, `Disarmed` (it disarmed mid-command), `NotPilot`
(someone else is flying), `LinkLost`. All are `DroneError`s.

## Safety

- **`max_throttle`** caps what your program can send. Keep it low while
  learning.
- A background thread sends the sticks 20 times a second. If your program
  hangs, crashes or loses Wi-Fi, the firmware disarms within 0.5 s.
- Only the program that called `arm()` steers. Another program or the web
  page can still watch and `kill()`.
- **No altitude hold.** `takeoff` and `land` only ramp the throttle. The
  right hover throttle depends on the battery and motors: find it with
  short, low hops and raise it a little at a time.

## Tests

```
cd software/dronekit_pcb
python -m unittest discover -s tests -v
```

16 tests, all against the simulator: flying, the safety rules, and the
error messages.
