# Hardware

KiCad project for the DroneKit Pro PCB. Licensed CERN-OHL-S v2.

**Commit the sources** (`.kicad_sch`, `.kicad_pcb`, `.kicad_pro`), not just gerbers.
Gerbers are build output and are gitignored by default.

## How the design is organised

Each circuit block is written as code (SKiDL) in its own folder, with a design
doc that explains its choices:

| Folder | Block |
|---|---|
| `power/` | 1S/2S + USB power path -> TPS63070 buck-boost 3.8V -> RT9013 / AP7361C 3.3V |
| `stm32/` | STM32F405 flight MCU: supplies, crystal, USB-C, boot, SWD (master pin map) |
| `dual-boot/` | ESP32-S3-WROOM-1 gating, bridge UART, strapping pins |
| `gyro/` | ICM-42688-P on SPI1 |
| `baro/` | SPA06-003 barometer on I2C1 |
| `motors/` | 4 x brushed low-side MOSFET drivers |
| `camera/` | 24-pin DVP camera on the ESP32-S3 + its 2.8V/1.2V rails |
| `elrs/` | optional serial ELRS receiver port |
| `buzzer/` | Betaflight beeper |
| `expansion/` | six JST-SH expansion headers |
| `mechanical/` | cage / PCB outline (Fusion) |
| **`board/`** | **all blocks merged into one KiCad schematic: start here for KiCad** |

`stm32f405-pinmap.md` is the human-readable pin allocation.

## Workflow

1. Edit a block's `.py`, run it (ERC must be clean).
2. Run `board/build_board.py` to regenerate `board/board.kicad_sch` and
   `board/board.net` (it cross-checks every shared pin and re-verifies the
   schematic's connectivity).
3. Open `board/board.kicad_pro` in KiCad 8, run ERC, then Tools > Update PCB
   from Schematic and lay out the board.
4. Clean DRC, then generate a JLCPCB fab quote and an LCSC BOM cost sheet
   (free, no purchase).
