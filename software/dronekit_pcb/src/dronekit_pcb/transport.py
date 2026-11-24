"""How a Drone talks to the firmware: one JSON text message at a time.

The real drone uses a WebSocket (``WebSocketTransport``). Tests and the
simulator use an in-process transport (see ``sim.py``). Anything with
``send``, ``recv`` and ``close`` works.
"""

from __future__ import annotations

from typing import Optional, Protocol


class Transport(Protocol):
    def send(self, text: str) -> None:
        """Send one JSON message. Raises ConnectionError if the link is gone."""

    def recv(self, timeout: float) -> Optional[str]:
        """Return the next message, or None if nothing arrived in time.
        Raises ConnectionError if the link is gone."""

    def close(self) -> None:
        """Close the link. Safe to call more than once."""


class WebSocketTransport:
    """WebSocket to the drone's firmware, e.g. ws://192.168.4.1/ws.

    Needs the ``websockets`` package (12 or newer)."""

    def __init__(self, url: str, open_timeout: float = 5.0):
        try:
            from websockets.sync.client import connect
        except ImportError as e:  # pragma: no cover - depends on the install
            raise ImportError(
                "dronekit_pcb needs the 'websockets' package to reach a real drone: "
                "pip install websockets"
            ) from e
        try:
            self._ws = connect(url, open_timeout=open_timeout)
        except OSError as e:
            raise ConnectionError(f"can't reach the drone at {url}: {e}") from e

    def send(self, text: str) -> None:
        from websockets.exceptions import ConnectionClosed

        try:
            self._ws.send(text)
        except ConnectionClosed as e:
            raise ConnectionError("link to the drone closed") from e

    def recv(self, timeout: float) -> Optional[str]:
        from websockets.exceptions import ConnectionClosed

        try:
            msg = self._ws.recv(timeout=timeout)
        except TimeoutError:
            return None
        except ConnectionClosed as e:
            raise ConnectionError("link to the drone closed") from e
        return msg if isinstance(msg, str) else msg.decode("utf-8")

    def close(self) -> None:
        self._ws.close()
