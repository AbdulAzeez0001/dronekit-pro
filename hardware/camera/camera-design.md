# Camera — 24-pin DVP module on the ESP32

Status: **decided (2026-11-22): DVP camera on an ESP32-S3-WROOM-1-N8R2.**
The dual-boot circuit (`hardware/dual-boot/`) is moved to the S3. The camera
connector and its rails are in `camera.py` (netlist `camera.net`, ERC clean).
The final cradle size waits on measuring the real module.

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
| PWDN | 14 (10k pull-up) | | D1 (Y3) | 9 |
| RESET | RC: 10k to 3.3 V, 100nF | | D0 (Y2) | 11 |

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

### 4. Camera block (`camera.py` → `camera.net`)

```
+3V3_ESP --> U30 XC6206P282MR --> +2V8_CAM  -> AVDD  (J30 pin 21)
+3V3_ESP --> U31 XC6206P122MR --> +1V2_CAM  -> DVDD  (J30 pin 15)
+3V3_ESP --------------------------------  -> DOVDD (J30 pin 14)
```

| Ref | Part | Note |
|---|---|---|
| J30 | 24-pin 0.5 mm FPC, flip-lock | footprint: Hirose FH12-24S-0.5SH, on the vision board's underside at the front edge (`hardware/board/README.md`, "vision placement"); **Hirose FH12-24S-0.5SH(55), LCSC C202112, bottom contact** (2026-11-26, from the module drawing: the ribbon's contacts face away from the lens, and must face the board at J30) |
| U30 | XC6206P282MR, SOT-23 | 2.8 V, e.g. LCSC C347374 (250 mA) |
| U31 | XC6206P122MR, SOT-23 | 1.2 V, e.g. LCSC C2827649 (200 mA). Not the Torex "-G" C424699, which is 60 mA |
| C30–C33 | 1 µF 0402 | LDO in/out |
| C34–C36 | 100 nF 0402 | at J30's DOVDD, DVDD, AVDD pins |
| R30 | 10k | PWDN pull-up |
| R31, R32 | 4.7k | SCCB (SIOD/SIOC) pull-ups |
| R33 + C37 | 10k + 100 nF | RESETB power-on RC |

Design choices:

- **PWDN pulls up.** The camera sits powered down unless the S3 drives
  GPIO14 low. In Mode A the S3 is held off, so the camera draws only standby
  current. It's the same dark-by-default idea as the S3's EN line.
- **The rails hang off `+3V3_ESP`.** The camera only works when the S3 does,
  and its current stays off the gyro's clean `+3V3_SYS` rail. Budget roughly
  100 mA extra while streaming. The 1.2 V LDO drops 2.1 V, so at about
  60 mA it dissipates about 0.13 W in SOT-23. That's fine, but keep some
  copper on its pads.
- **Y0/Y1 stay unconnected.** They're the low bits of the 10-bit bus, and
  the driver uses 8 bits.

**FPC pin numbering:** the pin numbers follow the SunFounder ESP32 camera
extension table (pin 1 = Y0, pin 24 = NC). Some ESP32-CAM schematics number
the same connector the other way round (pin 1 = NC … pin 24 = Y0). The
signal order is the same either way. What matters is which end of the
connector the ribbon's pin 1 lands on, so check the chosen connector against
the module before layout: AGND and DGND ring through to the module's metal
shield. **Checked 2026-11-26** against the OV2640-DVP module drawing (pin 1 =
STROBE … pin 24 = Y0): J30 pin n = module pin 25 − n for all 24 pins.

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
- [x] Add the camera block (24-pin FPC connector + 2.8V/1.2V LDOs) as circuit
      code: `camera.py`.
- [x] Pick the 2.8 V and 1.2 V LDOs (XC6206P282MR / XC6206P122MR).
- [ ] Confirm the XC6206 SOT-23 pin order (1 VSS, 2 VOUT, 3 VIN) on the
      chosen vendor's datasheet.
- [ ] Pick the exact FPC connector (LCSC) and check its pin-1 side against the
      module's ribbon.
- [ ] Measure the real module and set the final `cam_w` / `cam_d` in Fusion
      (currently a 9 mm estimate).
