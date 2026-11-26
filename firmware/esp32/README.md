# DroneKit Pro - ESP32-S3 firmware (MIT)

Runs on the vision board's ESP32-S3 in **Code mode** (boot switch open).
The STM32 only powers the ESP32-S3 in that mode (see
`firmware/betaflight/README.md`).

What it does:
- **Wi-Fi access point** `DroneKit-XXXX` at `192.168.4.1`, at most 2 clients.
- **Control panel** at `http://192.168.4.1/`: `software/control-panel/`,
  uploaded to the ESP32's flash with `pio run -t uploadfs`.
- **Bench-test page** at `http://192.168.4.1/bench` (built into the
  firmware, and at `/` too until the panel is uploaded): arm, disarm, kill,
  sliders, live telemetry.
- **WebSocket JSON API v1** at `ws://192.168.4.1/ws`. The message list is in
  `src/api.h`; `software/dronekit_pcb` should talk to this.
- **MSP link to Betaflight** on UART1 (GPIO1 RX, GPIO2 TX, 115200): RC
  frames (`MSP_SET_RAW_RC`) at 50 Hz, plus attitude, battery and status.

Not done yet: the camera (waits for J30, whose pin order isn't confirmed),
flashing the STM32 from the ESP32-S3 (BOOT0/NRST are wired but left
alone), and OTA updates of this firmware.

**Compiled on 2026-11-25** with PlatformIO 6.2.0 (espressif32 6.9.0,
Arduino core): no errors, and no warnings from `src/`. It uses 843 KB of
flash (25%) and 43 KB of RAM (13.5%); `pio run -t buildfs` also builds the
file image with the control panel. Not yet run on a board.

| File | What |
|---|---|
| `platformio.ini` | Build settings (Arduino core, ESP32-S3 N8R2) |
| `src/board_pins.h` | Pins, checked against `vision.kicad_pcb` |
| `src/msp.*` | MSP v1 framing and parser |
| `src/flight_link.*` | RC out, telemetry in, arming rules |
| `src/api.h` | WebSocket API v1 |
| `src/index_html.h` | Bench-test page (`/bench`) |
| `src/main.cpp` | Wi-Fi, web server, pilot handling |

## Build and flash

Install [PlatformIO](https://platformio.org/) (VS Code extension or
`pip install platformio`). Put the drone in Code mode, connect USB-C, then:

```
pio run -t upload        # the firmware
pio run -t uploadfs      # the control panel (software/control-panel)
pio device monitor
```

The console prints the Wi-Fi name and password every 10 seconds until a
device joins. If upload fails, hold the ESP program button (SW2) while
plugging in USB.

## The Wi-Fi password

Each board makes its own random 10-character password on first boot and
keeps it in flash, so two kits in one room don't share one. Read it on the
USB console. Writing it on a label on the drone is a good idea.

## Safety rules (in the code, not just here)

| Rule | Where |
|---|---|
| RC frames go out at 50 Hz all the time, so Betaflight sees a live link. If this firmware stops, Betaflight's own failsafe takes over. | `flight_link.cpp` |
| Only one pilot: the first client to send `control`. Others can watch, disarm and kill. | `main.cpp` |
| No `control` from the pilot for 500 ms, or the pilot disconnects: throttle to zero and disarm. | `main.cpp` |
| Arming needs the throttle at the bottom and a live link to the STM32. Betaflight applies its own arming checks on top. | `flight_link.cpp` |
| Disarmed: throttle is held at 1000 whatever the client sends. | `flight_link.cpp` |
| Kill (any client, the red button, or the space bar): disarm now. | `main.cpp`, page |
| BOOT0 is held low and NRST released, so the STM32 keeps running. Strapping pins are never driven. | `flight_link.cpp`, `board_pins.h` |

A disarm in the air drops the drone. That's the intended outcome for a
30 g indoor whoop.

## Bench test (props OFF)

1. Betaflight: paste `firmware/betaflight/cli-defaults.txt`, `save`. This
   maps ARM to AUX1, which this firmware uses.
2. Code mode, power up. Join `DroneKit-XXXX`, open `http://192.168.4.1/bench`.
3. Check: FC link true, battery voltage right, roll/pitch follow the drone
   when you tilt it.
4. Throttle up, press Arm: refused ("throttle must be at the bottom").
5. Throttle down, Arm: "Arm asked" true. "Betaflight armed" should follow.
   If it doesn't, "Arming blocked flags" says why (Betaflight's
   arming-disable flags; the Configurator lists their meanings).
6. Raise the throttle a little: the motors spin. Kill: they stop.
7. Arm again, then close the browser tab: within 0.5 s, disarmed.
8. Arm again, then switch Wi-Fi off on the phone: disarmed.
9. A second phone can watch and kill, but can't arm or steer.
