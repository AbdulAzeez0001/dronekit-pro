# DroneKit Pro - Betaflight (GPLv3)

| Path | What it is |
|---|---|
| `config/DRONEKITPRO/config.h` | Board config for the fc board (Betaflight 4.5 format) |
| `cli-defaults.txt` | Matching CLI settings, and the gyro alignment derivation |
| `src/dual_boot.c`, `src/dual_boot.h` | Dual-boot mode select (Fly / Code) |

Nothing here has been compiled yet.

## Building

1. Clone Betaflight and its config repository at the same release (4.5.x).
2. Copy `config/DRONEKITPRO/` into the config repository's `configs/`.
3. Copy `src/dual_boot.c` and `src/dual_boot.h` into Betaflight's
   `src/main/fc/`.
4. Add `fc/dual_boot.c` to `COMMON_SRC` in `mk/source.mk`. The file
   compiles to nothing unless `USE_DRONEKIT_DUAL_BOOT` is defined, so it's
   harmless for other boards.
5. In `src/main/fc/init.c`:
   - add `#include "fc/dual_boot.h"` with the other `fc/` includes;
   - call it just before `rxInit();`:

     ```c
     #ifdef USE_DRONEKIT_DUAL_BOOT
         dualBootInit();
     #endif
         rxInit();
     ```

     By then the saved config has been read (so the receiver choice is
     known) and the receiver hasn't started yet.
6. `make CONFIG=DRONEKITPRO`.

## Dual boot

The design is in `hardware/dual-boot/dual-boot-design.md`. At boot, the
STM32 reads the mode switch once:

| Switch SW1 | MODE_SENSE (PC13) | Mode | RC source | ESP32-S3 (ESP_EN, PB12) | USB-C goes to |
|---|---|---|---|---|---|
| closed | low | **Fly** | ELRS receiver (UART2, CRSF) | held off | STM32 (Configurator) |
| open | high | **Code** | ESP32-S3 over MSP (UART1) | on | ESP32-S3 |

- The receiver change in Code mode is for that boot only. The saved
  config keeps `RX_SERIAL`, so Fly mode always gets the ELRS receiver back.
- Flipping the switch while powered changes the USB routing at once (that's
  hardware) but not the mode. Power-cycle to change mode.
- Every failure ends in Fly with the ESP32-S3 off: ESP_EN's 10k pull-down
  holds it off until the code runs, and with the vision board unplugged,
  PC13's internal pull-down reads low.
- In Code mode the ESP32-S3 must send `MSP_SET_RAW_RC` frames on its
  UART1 (GPIO1/GPIO2) at 115200, including the arm switch channel.
  Betaflight's normal RC failsafe applies if they stop.

**Bench test before flying (props off):**
1. Fly mode: the ESP32-S3 stays dark, the Configurator connects over USB,
   and the Receiver tab moves with the radio.
2. Code mode: the ESP32-S3 starts. With MSP frames from the ESP32-S3, the
   Receiver tab follows them (check over the ESP32-S3's link, since USB now
   goes to the ESP32-S3). Stop the frames and check that RX loss shows.
3. Unplug the vision board and power up: the fc should come up in Fly.
