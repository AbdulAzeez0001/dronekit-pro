"""A simulated drone that follows the firmware's rules (API version 1).

Use it to try programs with no hardware:

    from dronekit_pcb import Drone
    from dronekit_pcb.sim import SimDrone

    with SimDrone() as sim, Drone(None, transport=sim.connect()) as drone:
        drone.arm()
        drone.takeoff(0.5)
        drone.hover(2)
        drone.land()
        print(sim.max_altitude)

It mirrors firmware/esp32/src/main.cpp and flight_link.cpp: one pilot,
0.5 s control timeout, arming only at low throttle, kill from anyone,
telemetry at 10 Hz. Betaflight is reduced to "arms when asked, unless an
arming-disable flag is set". The altitude is a toy, for printing only.
"""

from __future__ import annotations

import json
import queue
import threading
import time
from typing import Optional

CONTROL_TIMEOUT = 0.5
ARM_MAX_THROTTLE = 0.05
HOVER_THROTTLE = 0.40     # toy model: above this it climbs, below it sinks


class SimTransport:
    """One client's end of an in-process link to a SimDrone."""

    def __init__(self, sim: "SimDrone", client_id: int):
        self._sim = sim
        self.client_id = client_id
        self.inbox: "queue.Queue[str]" = queue.Queue()
        self.closed = False

    def send(self, text: str) -> None:
        if self.closed or not self._sim.running:
            raise ConnectionError("link to the simulated drone closed")
        self._sim._receive(self.client_id, text)

    def recv(self, timeout: float) -> Optional[str]:
        if self.closed:
            raise ConnectionError("link to the simulated drone closed")
        try:
            return self.inbox.get(timeout=timeout)
        except queue.Empty:
            if not self._sim.running:
                raise ConnectionError("the simulated drone stopped")
            return None

    def close(self) -> None:
        if not self.closed:
            self.closed = True
            self._sim._disconnect(self.client_id)


class SimDrone:
    def __init__(self, vbat: float = 4.1):
        self._lock = threading.RLock()
        self._clients: dict = {}
        self._next_id = 1
        self.running = True

        # firmware state
        self.pilot = 0
        self._last_control = 0.0
        self.sticks = {"roll": 0.0, "pitch": 0.0, "yaw": 0.0, "throttle": 0.0}
        self.armed_cmd = False

        # "Betaflight"
        self.fc_link = True
        self.arming_disabled = 0
        self.fc_armed = False
        self.vbat = vbat

        # toy physics
        self.altitude = 0.0
        self.max_altitude = 0.0
        self.heading = 0.0
        self.log: list = []           # every message received, for tests

        self._thread = threading.Thread(target=self._run, name="simdrone", daemon=True)
        self._thread.start()

    # ---- lifecycle -------------------------------------------------------------

    def __enter__(self) -> "SimDrone":
        return self

    def __exit__(self, *exc) -> None:
        self.stop()

    def stop(self) -> None:
        self.running = False
        self._thread.join(timeout=1)

    def connect(self) -> SimTransport:
        with self._lock:
            cid = self._next_id
            self._next_id += 1
            t = SimTransport(self, cid)
            self._clients[cid] = t
        t.inbox.put(json.dumps({"type": "hello", "api": 1, "fw": "sim", "mode": "code",
                                "client_id": cid}))
        return t

    # ---- firmware behaviour (main.cpp) ------------------------------------------

    def _say(self, cid: int, kind: str, msg: str) -> None:
        text = json.dumps({"type": kind, "msg": msg})
        with self._lock:
            targets = [self._clients[cid]] if cid else list(self._clients.values())
        for t in targets:
            t.inbox.put(text)

    def _drop_pilot(self, why: str) -> None:
        self.sticks = {k: 0.0 for k in self.sticks}
        self.armed_cmd = False
        self.pilot = 0
        self._say(0, "event", why)

    def _receive(self, cid: int, text: str) -> None:
        with self._lock:
            try:
                msg = json.loads(text)
            except ValueError:
                self._say(cid, "error", "bad JSON")
                return
            self.log.append((cid, msg))
            kind = msg.get("type")
            if kind == "control":
                if self.pilot not in (0, cid):
                    self._say(cid, "error", "another client is the pilot")
                    return
                self.pilot = cid
                self._last_control = time.monotonic()
                self.sticks = {
                    "roll": max(-1.0, min(1.0, float(msg.get("roll", 0)))),
                    "pitch": max(-1.0, min(1.0, float(msg.get("pitch", 0)))),
                    "yaw": max(-1.0, min(1.0, float(msg.get("yaw", 0)))),
                    "throttle": max(0.0, min(1.0, float(msg.get("throttle", 0)))),
                }
            elif kind == "arm":
                if self.pilot != cid:
                    self._say(cid, "error", "only the pilot can arm; send control first")
                elif self.sticks["throttle"] > ARM_MAX_THROTTLE:
                    self._say(cid, "error", "throttle must be at the bottom to arm")
                elif not self.fc_link:
                    self._say(cid, "error", "no link to the flight controller")
                else:
                    self.armed_cmd = True
            elif kind == "disarm":
                self.armed_cmd = False
                self._say(0, "event", "disarmed")
            elif kind == "kill":
                self._drop_pilot("kill: disarmed, pilot dropped")
            else:
                self._say(cid, "error", "unknown type")

    def _disconnect(self, cid: int) -> None:
        with self._lock:
            self._clients.pop(cid, None)
            if cid == self.pilot:
                self._drop_pilot("pilot disconnected: disarmed")

    # ---- the loop: timeouts, "Betaflight", telemetry -----------------------------

    def _run(self) -> None:
        last_tlm = 0.0
        last = time.monotonic()
        while self.running:
            now = time.monotonic()
            dt, last = now - last, now
            with self._lock:
                if self.pilot and now - self._last_control > CONTROL_TIMEOUT:
                    self._drop_pilot("pilot went quiet: disarmed")

                # Betaflight: arms on the switch unless something blocks it.
                if self.armed_cmd and not self.fc_armed and self.arming_disabled == 0:
                    self.fc_armed = True
                if not self.armed_cmd:
                    self.fc_armed = False

                thr = self.sticks["throttle"] if self.fc_armed else 0.0
                climb = (thr - HOVER_THROTTLE) * 4.0           # m/s, toy
                self.altitude = max(0.0, self.altitude + climb * dt)
                self.max_altitude = max(self.max_altitude, self.altitude)
                self.heading = (self.heading + self.sticks["yaw"] * 180 * dt * self.fc_armed) % 360
                self.vbat = max(3.3, self.vbat - thr * 0.002 * dt)

                if now - last_tlm >= 0.1:
                    last_tlm = now
                    text = json.dumps({
                        "type": "telemetry", "pilot_id": self.pilot,
                        "armed_cmd": self.armed_cmd, "armed": self.fc_armed,
                        "arming_disabled": self.arming_disabled, "fc_link": self.fc_link,
                        "vbat": round(self.vbat, 2),
                        "roll": round(self.sticks["roll"] * 30 * self.fc_armed, 1),
                        "pitch": round(self.sticks["pitch"] * 30 * self.fc_armed, 1),
                        "heading": round(self.heading),
                    })
                    for t in list(self._clients.values()):
                        t.inbox.put(text)
            time.sleep(0.01)
        with self._lock:
            for t in list(self._clients.values()):
                t.inbox.put(json.dumps({"type": "event", "msg": "simulator stopped"}))
