# Flight MCU — STM32F405RGT6 (LQFP64)

Status: circuit captured, ERC clean (`stm32.py` → `stm32.net`). Not yet laid
out.

This block is the STM32 and everything it needs to run: supplies,
decoupling, crystal, USB, boot and debug. It's also the **master pin
definition**:

- `U1` is defined here with all 64 real LQFP64 pin numbers.
- Every pin another block uses is tied to that block's net name.
- The other blocks' `U1` entries are stubs with local pin numbers. When
  merging, keep this block's `U1` and drop the stubs; the nets connect by
  name.
- All 21 cross-block nets (including BEEPER) were checked against the other
  netlists, and each name matches.

## Supplies (ST DS8626, section 5.1.6 power supply scheme)

| Pin(s) | Connection | Parts |
|---|---|---|
| VDD 19, 32, 48, 64 | +3V3_SYS | 100 nF at each pin (C90–C93) + 4.7 µF on one VDD pin (C94) |
| VDDA 13 / VSSA 12 | +3V3_SYS / GND (VDDA = VDD) | 100 nF (C95) + 1 µF (C96) |
| VBAT 1 | +3V3_SYS (no backup battery) | 100 nF (C99) |
| VCAP_1 31, VCAP_2 47 | — | 2.2 µF each, ESR < 2 Ω (C97, C98). The regulator stays on; the LQFP64 has no BYPASS_REG pin |
| VSS 18, 63 | GND | |

Place every decoupling cap right at its pin, or directly under it on the
other side of the board.

## Clock

- 8 MHz crystal on PH0/PH1, which Betaflight's STM32F405 targets expect.
- Load caps CL1 = CL2 = 20 pF, for a crystal specified at CL = 20 pF. That
  uses ST's rule CL = CL1·CL2/(CL1+CL2) + about 10 pF of pin and board
  capacitance.
- If the chosen crystal has a different CL, recalculate the caps.

## USB (Betaflight configurator)

| | |
|---|---|
| Connector | USB-C 16-pin (HRO TYPE-C-31-M-12 footprint) |
| Data | D+ → PA12, D− → PA11 (USB OTG FS), both rows of the connector tied |
| CC1 / CC2 | 5.1k pull-downs each, so a USB-C host sees a device |
| ESD | USBLC6-2SC6 on D+/D− |
| VBUS | powers the logic through the USB power path in `hardware/power/` (not the motors) |

**USB powers the logic, so no battery is needed for the configurator.**
VBUS goes to the power block, where a Schottky and the battery FET's gate
drive pick USB or battery without back-feeding the LiPo. See "USB power path"
in `hardware/power/power-design.md`. The motors run only from the battery,
so USB can never spin them.

## Boot, reset and debug

- **BOOT button (SW90):** connects BOOT0 to 3.3 V through 1k. Hold it while
  plugging in USB to enter DFU and flash Betaflight. The 1k protects the
  ESP32-S3's GPIO41, which also drives BOOT0 for OTA flashing.
  - BOOT0 already has its 10k pull-down in the dual-boot block.
- **BOOT1 (PB2):** 10k pull-down. System-memory boot needs BOOT1 = 0.
- **NRST:** has its 100 nF and ESP32-S3 open-drain control in the
  dual-boot block. There's no reset button; power-cycle, or use SWD.
- **SWD pads (J91):** 3V3, SWDIO (PA13), SWCLK (PA14), NRST, GND. For an
  ST-Link: debugging, and recovery if the bootloader is ever unreachable.
- **Status LED (D90):** on PB9 (Betaflight LED0), active low, through 1k.

## Pins used by this block

PH0/PH1 (crystal), PA11/PA12 (USB), PA13/PA14 (SWD), BOOT0, NRST, PB2
(BOOT1) and PB9 (LED0). Every other GPIO either belongs to another block or
is left free for expansion; see `hardware/stm32f405-pinmap.md`.

## To verify before layout

- [ ] Choose an 8 MHz 3225 crystal (CL = 20 pF) and confirm the load caps.
- [ ] Place the USB-C connector on an edge that's reachable with the battery
      fitted (check against the cage in Fusion).
- [ ] Optional: a ferrite or RC filter from VDD to VDDA if VBAT_SENSE
      readings are noisy.
