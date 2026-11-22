# RC receiver port — optional ExpressLRS add-on

Status: decided, ERC clean (`elrs.py` → `elrs.net`).

**The ELRS receiver is an optional add-on.** The kit ships without one. A
student or user who wants to fly with a radio transmitter buys any small
serial ELRS receiver and solders it to four pads. The board only provides
the port.

## Why optional, and why serial

- **Mode B needs no RC receiver.** Code mode is controlled by the ESP32-S3
  over WiFi. Only Mode A (Fly) with a radio transmitter needs one, so the
  base kit stays cheaper.
- **No RF design on the board.** An onboard SX1280 needs either a 25 × 14 mm
  module or a chip-down 2.4 GHz layout. The module didn't fit under the
  32 × 30 mm board next to the STM32; this was checked in Fusion.
- **The user can pick any ELRS receiver.** Small serial receivers are cheap
  and come in 2.4 GHz and 900 MHz versions.
- **It frees SPI3** (PC10–PC12, PA15, PB13–PB15) for expansion.

## The port (J60)

| Pad | Signal | STM32 | Wire on the receiver |
|---|---|---|---|
| 1 | GND | — | GND |
| 2 | PWR | +3V8 | 5V / VCC |
| 3 | FC_TX | PA2 (USART2_TX) via 100 Ω | RX |
| 4 | FC_RX | PA3 (USART2_RX) via 100 Ω | TX |

- **Wiring:** TX and RX cross over, so FC TX goes to the receiver's RX. The
  pad order matches the GND / 5V / RX / TX order printed on most small
  receivers, so the wires go straight across.
- **100 Ω series resistors** on both lines protect the STM32 if a receiver
  is soldered on the wrong way round.
- **10 µF + 100 nF at the pads** handle the receiver's TX bursts.

**Power:** the board has no 5 V rail, so the pads give +3V8.

- Many small ELRS receivers run an internal 3.3 V regulator from their
  "5V" pin, so 3.8 V may work, but **check the receiver's stated input range
  before recommending one for the kit**.
- If a receiver needs a true 5 V, the fix is a tiny boost converter, or
  feeding it from VBAT on 2S only.

## Betaflight setup (Mode A)

- Ports tab: UART2 → Serial Rx.
- Receiver tab: Serial-based receiver, provider **CRSF**.
- ELRS v3 receivers bind with a binding phrase or the bind button. That's
  set on the receiver side, not the FC.
- Without a receiver, Betaflight won't arm in Mode A. That's expected:
  Mode B (Code) still works.

## Assembly notes (for the kit docs)

- **Mount the receiver** inside the cage, away from the battery (a LiPo
  blocks RF) and away from the motors.
- **Antenna:** route it out through the cage, ideally vertical. Don't
  coil it or tape it to the battery.

## To verify before layout

- [ ] Pick one or two recommended receivers and confirm each accepts 3.8 V
      on its power pin.
- [ ] Put J60 at a board edge that's reachable with the battery fitted.
- [ ] Betaflight target: UART2 on PA2/PA3; remove the RX_SPI resources.
