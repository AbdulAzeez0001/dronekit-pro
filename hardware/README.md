# Hardware

KiCad project for the DroneKit Pro PCB. Licensed CERN-OHL-S v2.

**Commit the sources** (`.kicad_sch`, `.kicad_pcb`, `.kicad_pro`), not just gerbers.
Gerbers are build output and are gitignored by default.

Build first, in this order:
1. Dual-boot reset circuit (the differentiator). Verify ESP32 strapping pins
   GPIO0 / GPIO2 / GPIO15 are not fought by the boot switch or reset routing.
2. Full schematic: STM32F405 min system, ESP32-WROOM, MPU-6000 (SPI),
   BMP280 (I2C), power tree (XT30 -> MP2307 5V -> RT9013 3.3V), 4-in-1 ESC
   interface, ELRS SPI, buzzer FET, 6 expansion headers.
3. Layout, then clean ERC + DRC.
4. Generate a JLCPCB fab quote and an LCSC BOM cost sheet (free, no purchase).
