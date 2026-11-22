# Camera — 24-pin DVP module on the ESP32

Status: **decided (2026-11-22): DVP camera on an ESP32-S3-WROOM-1-N8R2.**
The dual-boot circuit (`hardware/dual-boot/`) is moved to the S3. The camera
connector, its 2.8V/1.2V rails and the cradle size are still to do.

## The part

A small 24-pin DVP camera module with a ribbon cable (FPC), the kind
used on ESP32-CAM boards. These are usually OV2640, sometimes
OV3660/OV5640 on the same 24-pin footprint. Confirm the sensor and the FPC
pinout with the seller before ordering. The ESP32-CAM reference schematic is
the usual source for the pinout.

| | |
|---|---|
| Interface | 8-bit parallel DVP + SCCB (I2C-like) control |
| Connector | 24-pin, 0.5 mm pitch FPC, flip-lock, on the FC board |
| Head size | about 8–9 mm square (measure the real module) |
| Supplies (OV2640) | 1.2 V core, 2.8 V analog, 3.3 V (or 2.8 V) I/O |
| Video path | ESP32 → WiFi (JPEG), Mode B (Code) only |

It feeds the ESP32 only. In Mode A (Fly) there is no analog video for FPV
goggles. If FPV flying in Mode A matters, an analog nano camera + VTX is the
other option. It's independent of the ESP32 but doesn't fit the browser
control panel.

## What it changes on the board

### 1. ESP32 module: needs PSRAM — recommend ESP32-S3-WROOM-1 (N8R2)

The camera driver (`esp32-camera`) needs PSRAM for anything beyond tiny frames.
The current ESP32-WROOM-32 has none. The two ways to fix that:

| | ESP32-WROVER | ESP32-S3-WROOM-1-N8R2 |
|---|---|---|
| PSRAM | yes | 2 MB (quad) |
| Size | 18 × 31.4 × 3.3 mm (longer) | 18 × 25.5 × 3.1 mm (same as WROOM-32) |
| Fits the 32 × 30 mm FC? | barely: 31.4 mm on a 32 mm board, no room for the antenna edge | yes, drop-in footprint size |
| GPIO16/17 | taken by PSRAM, so the STM32 bridge must move | free |
| Free GPIOs for camera | too few: 15 camera pins + bridge doesn't fit without using strap pins | plenty |
| Camera support | yes | yes, plus native USB |

Recommendation: **ESP32-S3-WROOM-1-N8R2**. Take the quad-PSRAM "R2" part, not
"R8". The octal-PSRAM R8 variants use GPIO35–37.

### 2. Dual-boot circuit has to be redone for the S3

`hardware/dual-boot/` is written for the ESP32-WROOM-32. The idea carries
over unchanged (EN pull-down, STM32 gates EN, UART bridge, ESP drives STM32
BOOT0/NRST). The pins and strapping rules are different:

| | ESP32 (current) | ESP32-S3 |
|---|---|---|
| Strapping pins | GPIO0, 2, 5, 12, 15 | GPIO0, 3, 45, 46 |
| Bridge UART | GPIO16/17 (UART2) | any free pins via the GPIO matrix |
| Programming | GPIO0 button + UART0 | GPIO0 button + native USB (GPIO19/20) or UART0 |

### 3. Proposed S3 pin plan (to verify against the S3 datasheet)

Camera pins follow Espressif's ESP32-S3-EYE board (checked against
`CAMERA_MODEL_ESP32S3_EYE` in arduino-esp32's `camera_pins.h`):

| Signal | S3 GPIO | | Signal | S3 GPIO |
|---|---|---|---|---|
| XCLK | 15 | | D7 (Y9) | 16 |
| SIOD (SDA) | 4 | | D6 (Y8) | 17 |
| SIOC (SCL) | 5 | | D5 (Y7) | 18 |
| VSYNC | 6 | | D4 (Y6) | 12 |
| HREF | 7 | | D3 (Y5) | 10 |
| PCLK | 13 | | D2 (Y4) | 8 |
| PWDN | tie low or spare GPIO | | D1 (Y3) | 9 |
| RESET | RC to 3.3 V | | D0 (Y2) | 11 |

Rest of the dual-boot wiring:

| Signal | S3 GPIO | Note |
|---|---|---|
| BRIDGE (S3 RX ← STM32 PA9) | 1 | UART1 via GPIO matrix |
| BRIDGE (S3 TX → STM32 PA10) | 2 | |
| STM_BOOT0 | 41 | was IO25 |
| STM_NRST (open-drain) | 42 | was IO26 |
| USB D− / D+ | 19 / 20 | native USB, optional |
| Program button | 0 | strap, 10k pull-up |

Nothing above touches GPIO3/45/46. Strap resistors are in `hardware/dual-boot/`
(GPIO0 pull-up, GPIO45 and GPIO46 pull-down, GPIO3 unconnected).

### 4. Power: two more rails for the camera

The OV2640 needs 2.8 V and 1.2 V from small LDOs fed from the 3.3 V
rail. The ESP32-CAM board does the same. The camera only runs in Mode B, so it
can sit on the ESP side, `+3V3_ESP`. Budget roughly 100 mA extra while
streaming. Part choice is open.

### 5. Mechanical

- The cradle can shrink from the 14 mm placeholder to about 9 mm.
- The FPC connector goes at the FC's front (+X) edge, so the ribbon
  folds straight forward to the camera.
- The ESP32-S3 module footprint matches what's already placed in Fusion.

## Before this is decided

- [x] Choose the camera: DVP module on the ESP32-S3 (WiFi video, Mode B).
- [ ] Measure the module: head size, lens height, FPC length.
- [ ] Confirm the sensor (OV2640?) and the FPC pinout from the seller.
- [x] Switch to ESP32-S3-WROOM-1-N8R2 and redo `hardware/dual-boot/` for the
      S3 strapping pins.
- [ ] Verify the S3 strap table against the ESP32-S3 datasheet.
- [ ] Add the camera block (24-pin FPC connector + 2.8V/1.2V LDOs) as circuit
      code next to `dual_boot.py`.
- [ ] Pick the 2.8 V and 1.2 V LDOs.
- [ ] Measure the real module and set the final `cam_w` / `cam_d` in Fusion
      (currently a 9 mm estimate).
