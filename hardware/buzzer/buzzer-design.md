# Buzzer — Betaflight beeper on PB8

Status: decided, ERC clean (`buzzer.py` → `buzzer.net`). Not yet laid out.

## What it's for

- **Arm and disarm beeps,** so you know the quad is live.
- **Low-battery warning.**
- **Lost-model alarm:** after a crash, switch it on from the transmitter and
  follow the sound. This matters on a small indoor whoop.

## Circuit

```
+3V8 ── J120 BZ+ ─[ buzzer ]─ BZ− ── Q120 AO3400A drain
                                     Q120 source ── GND
        D120 B5819W across the buzzer (cathode to +3V8)
STM32 PB8 ── 22 Ω ──┬── Q120 gate
                    10k ── GND
C120 1 µF on +3V8 at the pads
```

| Ref | Part | Why |
|---|---|---|
| Q120 | AO3400A | low-side switch. It's the same FET as the motor drivers, so one fewer part on the BOM |
| D120 | B5819W | flyback diode: magnetic buzzers are inductive. Same part as the USB power path |
| R120 | 22 Ω | gate series |
| R121 | 10k | gate pull-down, so it stays silent while the STM32 boots |
| C120 | 1 µF | local decoupling at the pads |
| J120 | 2 pads | BZ+ and BZ− for an external buzzer |

## Design choices

- **Pads, not an onboard buzzer.** A loud buzzer is 9–12 mm across, too big
  for the 32 × 30 mm board, and some builders will skip it. The pads take
  any small **active** buzzer: the kind that beeps by itself when it gets
  power. Mind the polarity: + goes to BZ+.
- **Powered from +3V8.**
  - Not VBAT: on 2S, VBAT reaches 8.4 V, too much for a 5 V buzzer.
  - There's no 5 V rail. A 5 V active buzzer at 3.8 V is a bit quieter but
    works, and a 3 V-rated one is louder.
  - Never `+3V3_SYS`: that keeps buzzer current spikes off the gyro's rail.
- **Current:** a small active buzzer draws about 20–40 mA, well within the
  buck-boost's margin.

## Betaflight setup

| Setting | Value |
|---|---|
| `resource BEEPER 1` | B08 |
| `beeper_inversion` | OFF (PB8 high = FET on = beep) |
| `beeper_od` | OFF (push-pull drive into the gate) |

Beeper conditions (arming, low battery, RX lost, and so on) are set in the
configurator's Configuration tab.

A passive buzzer would need a PWM tone. Betaflight can do that with
`beeper_frequency`, but an active buzzer is simpler and is the
recommendation.

## To verify before layout

- [ ] Pick a recommended buzzer for the kit docs: active, 3–5 V, ≤ 40 mA,
      about 9 mm, and check it's loud enough at 3.8 V.
- [ ] Put J120 where the buzzer can sit on the board or the cage without
      touching a prop.
