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
- All 28 cross-block nets (including BEEPER and the expansion headers) were
  checked against the other netlists, and each name matches.

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

## USB: one port for both chips

The single USB-C port goes to the STM32 or the ESP32-S3, chosen by the
boot-mode switch:

| Mode switch | USB-C connects to | Used for |
|---|---|---|
| Mode A (Fly), MODE_SENSE low | STM32 PA12/PA11 (USB OTG FS) | Betaflight configurator, DFU flashing |
| Mode B (Code), MODE_SENSE high | ESP32-S3 IO20/IO19 (native USB) | flashing the ESP32-S3, Python REPL / serial console |

| | |
|---|---|
| Connector | USB-C 16-pin (HRO TYPE-C-31-M-12 footprint), both rows of D+/D− tied |
| Switch | TI TS3USB221A (U92), a USB 2.0 2:1 analog switch, UQFN-10 |
| Switch control | S = MODE_SENSE (low: port 1 = STM32, high: port 2 = ESP32-S3); OE tied low (always on); VCC on +3V3_SYS with 100 nF (C103) |
| CC1 / CC2 | 5.1k pull-downs each, so a USB-C host sees a device |
| ESD | USBLC6-2SC6 on D+/D−, on the connector side of the switch |
| VBUS | powers the logic through the USB power path in `hardware/power/` (not the motors) |

The switch pinout and truth table are from TI's TS3USB221A datasheet
(SCDS277C): pin table 4-1, truth table 7-1, VCC 2.3–3.6 V. Flipping the Mode
switch with the cable plugged in simply re-enumerates the device on the PC.

**Why it's built this way:**

- **Code mode needs USB on the ESP32-S3.** It's the chip that runs the
  student's code, and its ROM bootloader only listens on UART0 or native USB.
  The STM32 bridge uses UART1, so it can't reach the bootloader.
- **The ESP32-S3's built-in USB serial/JTAG** lets esptool flash it with no
  adapter and no buttons, and gives a serial console for Python.
- **One port is simpler for students.** There's no second connector to
  find, and the Mode switch already says which chip they're talking to.
- **Recovery:** if the ESP32-S3 firmware ever breaks USB, the UART0 pads
  in the dual-boot block are the way back in.

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

PH0/PH1 (crystal), PA11/PA12 (USB, via the U92 switch), PA13/PA14 (SWD), BOOT0, NRST, PB2
(BOOT1) and PB9 (LED0). Every other GPIO either belongs to another block or
is left free for expansion; see `hardware/stm32f405-pinmap.md`.

## To verify before layout

- [ ] Choose an 8 MHz 3225 crystal (CL = 20 pF) and confirm the load caps.
- [ ] Place the USB-C connector on an edge that's reachable with the battery
      fitted (check against the cage in Fusion).
- [ ] Optional: a ferrite or RC filter from VDD to VDDA if VBAT_SENSE
      readings are noisy.
