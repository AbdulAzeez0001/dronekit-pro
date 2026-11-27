# Motor drivers — 4 × brushed, low-side MOSFET

Status: decided, ERC clean (`motors.py` → `motors.net`). Not yet laid out or
built. This replaces the old 4-in-1 ESC: the motors are now brushed 8×20
coreless motors (BetaFPV 15000 KV; 7×20 until 2026-11-26), driven by plain PWM.

## One channel

```
VBAT_RAW ──┬──────────────┐
           │              │
        motor +        SS54 (cathode)
        motor − ───────┴─ (anode) ── AO3400A drain
                                     AO3400A source ── GND
STM32 TIM3 pin ── 22 Ω ──┬── gate
                         10k ── GND
```

×4, identical. Refs 40–47 per part type; see the BOM.

## Parts

| Ref | Part | Rating | Why |
|---|---|---|---|
| Q40–Q43 | AO3400A, SOT-23 | 30 V, 5.7 A, Vgs ±12 V, Rds(on) specified at Vgs 2.5 V | logic-level, so the STM32's 3.3 V turns it fully on |
| D40–D43 | SS54, SMA (C22452) | 40 V, 5 A Schottky | flyback; margin over the 8×20 stall current. Was SS34 (3 A) for 7×20; same footprint |
| R40–R43 | 22 Ω 0402 | | gate series: damps ringing, limits pin current |
| R44–R47 | 10k 0402 | | gate pull-down: motor off until the firmware drives it |
| C40, C41 | 22 µF / 25 V 0805 | | VBAT_RAW bulk at the motor pads |
| J40–J43 | 2 solder pads each | | M+ = VBAT_RAW, M− = FET drain |

## Design choices

- **Gate pull-downs.** STM32 pins float until Betaflight starts. A floating
  gate can turn a FET partly on, and the props would twitch at power-up. The
  pull-downs keep every motor off until firmware drives it. That's the same
  dark-by-default rule as the ESP32-S3 EN line.
- **A flyback diode on every motor (don't omit it).** Brushed motors are
  inductors. At each PWM turn-off, the motor current has to keep flowing.
  The Schottky gives it a path back to VBAT_RAW instead of avalanching the
  FET.
- **Everything is rated for 2S.** The FETs are 30 V and the diodes 40 V, so
  the board survives a 2S pack (8.4 V). The 8×20 motors themselves are
  1S motors; see the power doc for the `motor_output_limit` rule on 2S.
- **The motors run from VBAT_RAW,** before the logic's reverse-polarity FET.
  Motor current is several amps, far more than the AO3401A carries.
  - **The consequence:** a reversed battery shorts through the FET body
    diodes and the flyback diodes.
  - **The rule:** use a keyed battery connector, and never a bare pigtail
    that can go on backwards.
- **Heat:** at roughly 3 A per 8×20 motor at full throttle, each AO3400A
  (about 35 mΩ at a 3.3 V gate) dissipates about 0.3 W. That's fine in
  SOT-23 with a copper pour on the drain pad. If motors run hot or stall
  often, a DFN 2 × 2 FET with lower Rds(on) is the upgrade.
- **Smaller diode option:** if the SMA diodes don't fit the 32 × 30 mm
  board, a 3 A / 40 V Schottky in SOD-123FL is the swap. Keep it ≥ 2 A and
  ≥ 20 V.

## STM32 pins and motor positions

All four motors are on TIM3, so they share one PWM frequency (Betaflight
`motor_pwm_protocol = BRUSHED`). The positions are Betaflight Quad-X, with
the board's +X = front and +Y = left:

| Motor | STM32 pin | Timer | Position | Cage corner (x, y mm) |
|---|---|---|---|---|
| M1 | PB0 | TIM3_CH3 | rear right | (−26.5, −26.5) |
| M2 | PB1 | TIM3_CH4 | front right | (+26.5, −26.5) |
| M3 | PB4 | TIM3_CH1 | rear left | (−26.5, +26.5) |
| M4 | PB5 | TIM3_CH2 | front left | (+26.5, +26.5) |

- **Spin direction** is set by which wire goes to M+. Swap the two wires to
  reverse a brushed motor. Match the directions to Betaflight's Motors tab
  for the chosen props-in or props-out setting.
- **Layout:** put each channel (FET, diode and pads) at its board corner.
  That keeps the high-current loop short and next to where the motor wires
  come through the cage's holder bases.

## To verify before layout

- [ ] Measure the 8×20 motor's stall current at 4.2 V on the bench. The
      SS54 diodes (5 A) and AO3400A FETs (5.7 A) should cover it; if it's
      over about 5 A, move to a bigger FET.
- [ ] Confirm the AO3400A and SS54 pinouts on the chosen LCSC vendor's
      datasheet (SOT-23: 1 G, 2 S, 3 D; SMA: 1 K, 2 A).
- [ ] Pick a keyed battery connector (see the power doc).
- [ ] Betaflight target: set the four TIM3 pins as brushed motor outputs.
