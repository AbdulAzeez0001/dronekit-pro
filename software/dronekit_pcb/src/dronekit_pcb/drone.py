"""Fly a DroneKit Pro in Code mode over its WebSocket API (version 1).

    from dronekit_pcb import Drone

    with Drone("192.168.4.1") as drone:
        drone.arm()
        drone.takeoff(throttle=0.45)
        drone.move(pitch=0.2, seconds=1)
        drone.land()

Leaving the ``with`` block for any reason (the end, an error, Ctrl+C)
disarms the drone.

There's no altitude hold yet: ``takeoff`` and ``land`` ramp the throttle up
and down, they don't hold a height. Start low and in a clear space.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, replace
from typing import Callable, Optional

from .errors import ArmError, Disarmed, LinkLost, NotPilot, arming_disable_names
from .transport import Transport, WebSocketTransport

API_VERSION = 1

CONTROL_PERIOD = 0.05     # send sticks at 20 Hz; the firmware drops a pilot after 0.5 s
TELEMETRY_TIMEOUT = 1.0   # no telemetry for this long = link lost


@dataclass(frozen=True)
class Telemetry:
    """The drone's latest report (10 times a second)."""

    pilot: bool = False             # this Drone is the pilot
    armed_cmd: bool = False         # the ESP32 is asking Betaflight to arm
    armed: bool = False             # Betaflight reports armed
    arming_disabled: int = 0        # Betaflight's arming-disable flags
    fc_link: bool = False           # the ESP32 hears the flight controller
    vbat: float = 0.0               # battery, volts
    roll: float = 0.0               # degrees
    pitch: float = 0.0              # degrees
    heading: float = 0.0            # degrees
    time: float = 0.0               # time.monotonic() when it arrived

    @property
    def arming_blocked_by(self) -> list:
        """Names of the Betaflight checks stopping it arming."""
        return arming_disable_names(self.arming_disabled)


@dataclass
class Sticks:
    roll: float = 0.0       # -1 (left) .. 1 (right)
    pitch: float = 0.0      # -1 (back) .. 1 (forward)
    yaw: float = 0.0        # -1 (left) .. 1 (right)
    throttle: float = 0.0   # 0 .. 1


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(v)))


class Drone:
    """A connection to one drone.

    host: the drone's address ("192.168.4.1"), or None when passing a
        ready-made ``transport`` (the simulator does this).
    max_throttle: the highest throttle this program may send (0..1). Keep
        it modest while learning.
    """

    def __init__(self, host: Optional[str] = "192.168.4.1", *,
                 transport: Optional[Transport] = None,
                 max_throttle: float = 0.7,
                 connect_timeout: float = 5.0):
        if transport is None:
            if host is None:
                raise ValueError("give a host or a transport")
            transport = WebSocketTransport(f"ws://{host}/ws", open_timeout=connect_timeout)
        self._t = transport
        self.max_throttle = _clamp(max_throttle, 0.0, 1.0)

        self._lock = threading.Lock()
        self._sticks = Sticks()
        self._tlm = Telemetry()
        self._client_id: Optional[int] = None
        self._errors: list = []       # error messages from the firmware, oldest first
        self._events: list = []
        self._closed = threading.Event()
        # Only a program that wants to fly sends sticks (and so becomes the
        # pilot). Set by arm(); cleared by kill(). Watchers never claim it.
        self._flying = threading.Event()
        self._link_error: Optional[BaseException] = None

        self._reader = threading.Thread(target=self._read_loop, name="dronekit-read", daemon=True)
        self._reader.start()
        try:
            hello = self._wait(lambda: self._client_id is not None, connect_timeout)
            if not hello:
                raise LinkLost("the drone didn't say hello")
        except BaseException:
            self.close()
            raise

        self._writer = threading.Thread(target=self._control_loop, name="dronekit-control", daemon=True)
        self._writer.start()

    # ---- context manager: always disarm on the way out ------------------------

    def __enter__(self) -> "Drone":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        """Disarm and disconnect. Safe to call more than once."""
        if self._closed.is_set():
            return
        try:
            self._send({"type": "kill"})
        except ConnectionError:
            pass
        self._closed.set()
        self._t.close()

    # ---- state -----------------------------------------------------------------

    @property
    def telemetry(self) -> Telemetry:
        with self._lock:
            return self._tlm

    @property
    def armed(self) -> bool:
        return self.telemetry.armed

    @property
    def battery(self) -> float:
        return self.telemetry.vbat

    # ---- commands --------------------------------------------------------------

    def arm(self, timeout: float = 3.0) -> None:
        """Arm, with the throttle at zero. Waits until Betaflight reports armed.

        Raises ArmError with the reason if it doesn't."""
        self._check_link()
        self.set_sticks(Sticks())
        # Become the pilot first: the firmware only lets the pilot arm.
        self._flying.set()
        if not self._wait(lambda: self._tlm.pilot, 1.0):
            self._flying.clear()
            raise NotPilot("another client is flying this drone")
        seen = len(self._errors)
        self._send({"type": "arm"})
        if self._wait(lambda: self._tlm.armed or len(self._errors) > seen, timeout):
            with self._lock:
                if self._tlm.armed:
                    return
                msg = self._errors[-1]
            raise ArmError(msg)
        blocked = self.telemetry.arming_blocked_by
        why = ("Betaflight won't arm: " + ", ".join(blocked)) if blocked else "Betaflight didn't arm in time"
        raise ArmError(why)

    def disarm(self) -> None:
        """Stop the motors."""
        self.set_sticks(Sticks())
        self._send({"type": "disarm"})

    def kill(self) -> None:
        """Stop the motors now (same as the red button), and stop being the
        pilot. Any connection can kill."""
        self._flying.clear()
        self.set_sticks(Sticks())
        self._send({"type": "kill"})

    def set_sticks(self, sticks: Sticks) -> None:
        """Set the sticks the background thread keeps sending."""
        s = Sticks(
            roll=_clamp(sticks.roll, -1, 1),
            pitch=_clamp(sticks.pitch, -1, 1),
            yaw=_clamp(sticks.yaw, -1, 1),
            throttle=_clamp(sticks.throttle, 0, self.max_throttle),
        )
        with self._lock:
            self._sticks = s

    @property
    def sticks(self) -> Sticks:
        with self._lock:
            return replace(self._sticks)

    def takeoff(self, throttle: float = 0.45, ramp: float = 1.0) -> None:
        """Ramp the throttle from 0 to `throttle` over `ramp` seconds.

        Open loop: no altitude hold. Find your drone's hover throttle with
        short, low hops first."""
        self._require_armed()
        self._ramp_throttle(0.0, throttle, ramp)

    def hover(self, seconds: float) -> None:
        """Keep the current throttle, sticks centred, for `seconds`."""
        self.move(seconds=seconds)

    def move(self, roll: float = 0.0, pitch: float = 0.0, yaw: float = 0.0,
             seconds: float = 1.0) -> None:
        """Hold these stick positions (-1..1) at the current throttle, then
        centre them again."""
        self._require_armed()
        throttle = self.sticks.throttle
        self.set_sticks(Sticks(roll, pitch, yaw, throttle))
        try:
            self._sleep_armed(seconds)
        finally:
            self.set_sticks(Sticks(0, 0, 0, self.sticks.throttle))

    def land(self, seconds: float = 2.0) -> None:
        """Ramp the throttle down to 0 over `seconds`, then disarm."""
        if self.armed:
            try:
                self._ramp_throttle(self.sticks.throttle, 0.0, seconds)
            except Disarmed:
                pass
        self.disarm()

    def wait_for(self, condition: Callable[[Telemetry], bool], timeout: float) -> bool:
        """Wait until condition(telemetry) is true. Returns False on timeout."""
        return self._wait(lambda: condition(self._tlm), timeout)

    # ---- internals -------------------------------------------------------------

    def _send(self, msg: dict) -> None:
        if self._closed.is_set():
            raise LinkLost("the connection is closed")
        self._t.send(json.dumps(msg))

    def _check_link(self) -> None:
        if self._link_error is not None:
            raise LinkLost(str(self._link_error))
        if self._closed.is_set():
            raise LinkLost("the connection is closed")
        tlm = self.telemetry
        if tlm.time and time.monotonic() - tlm.time > TELEMETRY_TIMEOUT:
            raise LinkLost("no telemetry from the drone for over a second")

    def _require_armed(self) -> None:
        self._check_link()
        if not self.armed:
            raise Disarmed("the drone isn't armed")

    def _sleep_armed(self, seconds: float) -> None:
        end = time.monotonic() + max(0.0, seconds)
        while True:
            self._require_armed()
            left = end - time.monotonic()
            if left <= 0:
                return
            time.sleep(min(0.05, left))

    def _ramp_throttle(self, start: float, stop: float, seconds: float) -> None:
        stop = _clamp(stop, 0, self.max_throttle)
        t0 = time.monotonic()
        seconds = max(0.0, seconds)
        while True:
            self._require_armed()
            k = 1.0 if seconds == 0 else min(1.0, (time.monotonic() - t0) / seconds)
            s = self.sticks
            s.throttle = start + (stop - start) * k
            self.set_sticks(s)
            if k >= 1.0:
                return
            time.sleep(0.05)

    def _wait(self, cond: Callable[[], bool], timeout: float) -> bool:
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            with self._lock:
                if cond():
                    return True
            if self._link_error is not None:
                raise LinkLost(str(self._link_error))
            time.sleep(0.01)
        with self._lock:
            return cond()

    def _control_loop(self) -> None:
        while not self._closed.wait(CONTROL_PERIOD):
            if not self._flying.is_set():
                continue
            s = self.sticks
            try:
                self._send({"type": "control", "roll": s.roll, "pitch": s.pitch,
                            "yaw": s.yaw, "throttle": s.throttle})
            except (ConnectionError, LinkLost) as e:
                if not self._closed.is_set():
                    self._link_error = e
                return

    def _read_loop(self) -> None:
        while not self._closed.is_set():
            try:
                text = self._t.recv(0.1)
            except ConnectionError as e:
                if not self._closed.is_set():
                    self._link_error = e
                return
            if text is None:
                continue
            try:
                msg = json.loads(text)
            except ValueError:
                continue
            self._handle(msg)

    def _handle(self, msg: dict) -> None:
        kind = msg.get("type")
        with self._lock:
            if kind == "hello":
                if msg.get("api") != API_VERSION:
                    self._link_error = LinkLost(
                        f"drone speaks API {msg.get('api')}, this package speaks {API_VERSION}")
                self._client_id = msg.get("client_id")
            elif kind == "telemetry":
                self._tlm = Telemetry(
                    pilot=msg.get("pilot_id") == self._client_id and self._client_id is not None,
                    armed_cmd=bool(msg.get("armed_cmd")),
                    armed=bool(msg.get("armed")),
                    arming_disabled=int(msg.get("arming_disabled", 0)),
                    fc_link=bool(msg.get("fc_link")),
                    vbat=float(msg.get("vbat", 0.0)),
                    roll=float(msg.get("roll", 0.0)),
                    pitch=float(msg.get("pitch", 0.0)),
                    heading=float(msg.get("heading", 0.0)),
                    time=time.monotonic(),
                )
            elif kind == "error":
                self._errors.append(str(msg.get("msg", "")))
            elif kind == "event":
                self._events.append(str(msg.get("msg", "")))
