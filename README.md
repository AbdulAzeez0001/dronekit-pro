# DroneKit Pro

**The programmable dual-boot PCB drone kit. Fly it with your phone. Code it in Python. Extend it with plug-in radio modules.**

DroneKit Pro is an open-hardware micro quadcopter kit built around a single pre-populated PCB frame. Flip the boot switch one way and it is a stable RC quad running Betaflight. Flip it the other way and it becomes a WiFi-connected programmable robot that runs your Python or Blockly code in the air.

Built for students, makers, teachers, and engineers.

> **Status:** Active development. The hardware design is not yet DRC-clean and the kit has not been physically built or flown. Do not order parts against this repo yet.

---

## The dual-boot idea

DroneKit Pro is two drones in one body:

- **Mode A (Fly)** — boot switch LOW. STM32F405 runs Betaflight, ESP32 off. Fly at 250Hz over ExpressLRS with full PID stabilisation.
- **Mode B (Code)** — boot switch HIGH. ESP32 opens a WiFi AP. Control from a browser at `192.168.4.1`, run Python via `dronekit_pcb`, or drag-and-drop Blockly. STM32 acts as motor co-processor.

---

## Specs (target)

| | |
|---|---|
| Frame | 130mm PCB-integrated, 1.6mm FR4 4-layer |
| Flight MCU | STM32F405RGT6 |
| Programmable MCU | ESP32-S3-WROOM-1-N8R2 (PSRAM, for the camera) |
| Camera | 24-pin DVP module (OV2640-class) on the ESP32-S3, WiFi video in Mode B |
| IMU / Baro | MPU-6000 (SPI) / BMP280 (I2C) |
| Motors | 4x 720 brushed coreless (7 x 20mm) |
| Motor drive | 4x AO3400A low-side MOSFET + SS34 flyback, brushed PWM (no ESC) |
| RX | ExpressLRS EP1 (SPI) |
| Battery | 1S or 2S LiPo (board runs from either; 1S for the brushed whoop) |
| Build time | 3-4 hours (first build) |
| Target price | TBD - pending verified JLC/LCSC BOM quote |

> The original concept targeted ~50,000 NGN all-inclusive. That number is held as unverified until a real fab + BOM quote confirms it. See `docs/` for the cost analysis once generated.

---

## Repo layout

```
hardware/    KiCad project, gerbers, BOM, JLC fab files   (CERN-OHL-S)
firmware/    esp32/ + betaflight/ custom STM32F405 target  (MIT / GPLv3*)
software/    dronekit_pcb pip package + control-panel UI    (MIT)
simulation/  eCalc inputs, lightweight Python dynamics sim  (MIT)
docs/        kit documentation, assembly guide              (CC-BY-SA 4.0)
```

\* The Betaflight target is a derivative of Betaflight and is therefore GPLv3, regardless of the rest of the firmware.

---

## Licensing

This project is multi-licensed because hardware, software, and docs need different terms:

- **Hardware** (`hardware/`): CERN-OHL-S v2 — strongly reciprocal. See `LICENSE-hardware`.
- **Firmware + software** (`firmware/`, `software/`, `simulation/`): MIT, except the Betaflight target which is GPLv3. See `LICENSE-software`.
- **Documentation** (`docs/`): CC-BY-SA 4.0.

---

## Roadmap

- [ ] Dual-boot reset circuit verified on paper (datasheet-level, ESP32 strapping pins checked)
- [ ] Full schematic captured in KiCad
- [ ] PCB layout, ERC + DRC clean
- [ ] JLCPCB fab quote + LCSC BOM cost sheet
- [ ] Betaflight custom target for STM32F405
- [ ] ESP32 firmware: WiFi AP, control panel, WebSocket API, STM32 bridge
- [ ] `dronekit_pcb` Python package + simulated drone
- [ ] First physical board built and bench-tested
- [ ] First flight
