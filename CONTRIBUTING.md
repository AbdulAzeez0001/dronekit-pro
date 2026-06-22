# Contributing

Thanks for your interest in DroneKit Pro.

- **Hardware** changes (KiCad) are licensed CERN-OHL-S v2. By contributing you
  agree your hardware contributions are released under that licence.
- **Software** contributions are MIT (Betaflight target excepted: GPLv3).
- **Docs** are CC-BY-SA 4.0.

Before opening a PR:
- Hardware: ERC + DRC must pass. Include a note on what you changed and why.
- Software: keep the WebSocket JSON API stable, or version it.
- One logical change per PR. Keep commits readable.

This is a real flying device. Anything affecting motor output, arming, or
power must be reviewed carefully. Safety over speed.
