# Power section — 1S or 2S input, split rails

Status: decided. The board runs from a **1S or 2S LiPo** with nothing to
change between them, **or from USB** (logic only) for the configurator and
bench coding. Parts to verify on LCSC before layout.

Source of truth: `power.py`, which generates `power.net` (ERC clean).

## Topology

```
1S/2S LiPo (VBAT_RAW, 3.0–8.4 V)
  ├─ motors (hardware/motors/: 4 × AO3400A + SS34, straight off the battery)
  ├─ 10k/1k divider ─> VBAT_SENSE (STM32 PC1)
  └─ Q10 AO3401A P-FET (reverse polarity + USB auto-select) ─> VBAT
USB-C VBUS (5 V) ─ D10 B5819W Schottky ─> VBAT     (and VBUS ─ 1k ─> Q10 gate)
VBAT ─ TPS63070 buck-boost ─> +3V8
        ├─ RT9013-33  ─> +3V3_SYS   STM32, ICM-42688-P, SPA06-003
        └─ AP7361C-33 ─> +3V3_ESP   ESP32-S3, camera (2V8/1V2 LDOs)
```

## Why a buck-boost to 3.8 V

- **1S drops below 3.3 V.** A 1S cell is 4.2 V full, but it sags to about
  3.0 V under brushed-motor load. A plain buck can't hold 3.3 V there.
- **2S is above everything.** A 2S pack is 6.0–8.4 V, so a plain boost can't
  be used either.
- **The TPS63070 covers both.** It's a buck-boost that takes 2.0–16 V in,
  switches between buck and boost mode by itself, and keeps running until the
  input falls to 1.85 V (UVLO). One part, no jumper.
- **It makes 3.8 V, not 3.3 V.** That leaves headroom for the two LDOs from
  the earlier design, which stay in:
  - They keep the split rails, so ESP32 WiFi bursts can't sag the gyro supply.
  - They filter the converter's 2.4 MHz ripple off the gyro rail.
  - The cost is about 0.5 V × 0.8 A ≈ 0.4 W at peak, split across the two
    LDOs. Typical load is about half that.

## Current budget

| Rail | Loads | Typical | Peak |
|---|---|---|---|
| +3V3_SYS | STM32F405, ICM-42688-P, SPA06-003 | ~150 mA | ~180 mA |
| +3V8 direct | optional ELRS receiver (J60) + buzzer (J120) + UART/LED/PWM headers | ~50 mA | ~240 mA |
| +3V3_ESP | ESP32-S3 (+ camera ~100 mA, Mode B) + 3V3 header modules (~100 mA budget) | ~220 mA | ~700 mA (TX burst) |
| +3V8 total | both LDOs + receiver, buzzer and headers | ~420 mA | ~1.1 A |

Battery current for the logic at peak:

- At 1S, 3.0 V in: 3.8 V × 1.1 A ÷ 0.9 ÷ 3.0 V ≈ 1.5 A (everything at peak at once). That's
  inside the 3.6 A switch limit.
- At 2S, 7.4 V in: about 0.5 A.

## TPS63070 design (TI SLVSC58B Rev. B, section 9.2)

| Ref | Value | Why |
|---|---|---|
| U10 | TPS63070RNM, VQFN-HR 15 (2.5 × 3 mm) | adjustable version |
| L10 | 1.5 µH, Coilcraft XFL4020-152ME (4 × 4 × 2.1 mm, Isat 4.6 A) | TI's typical value. Any shielded 1.5 µH with Isat ≥ 2 A and low DCR works |
| C10, C11 | 10 µF / 25 V 0805 | input, 2 parts needed above 6 V in |
| C12 | 10 µF / 25 V 0603 | input, right at the VIN pins |
| C13, C14 | 22 µF / 16 V 0805 | output, 2 parts for Vout ≤ 5 V |
| C15 | 10 µF 0603 | output, right at the VOUT pins |
| C16 | 100 nF | VAUX (internal regulator) |
| R11 / R12 | 374k / 100k | Vout = 0.8 V × (1 + R11/R12) = 3.79 V |
| R13 | 100k | EN to VIN through a series resistor, as TI recommends (1k–1M) |
| R14 | 100k | PG pull-up (net `PG_3V8`, free to route to an STM32 pin) |

How the control pins are tied:

- **PS/SYNC → GND: forced fixed-frequency PWM.** The steady 2.4 MHz ripple
  is easier for the LDOs to reject than power-save bursts.
- **VSEL → GND, FB2 open:** one output voltage.
- **Duty cycle at 8.4 V in:** 3.8 / 8.4 = 45%. TI's buck-mode minimum is 30%.
- **Footprint:** there's no stock KiCad footprint for RNM0015A, so import
  TI's.

## Reverse polarity: AO3401A, not DMG3415U

- The P-FET sits high-side: drain to the battery, source to the load, gate
  to GND through 100k.
- The old DMG3415U is rated Vgs ±8 V, and a full 2S pack puts 8.4 V on the
  gate. The AO3401A is rated Vgs ±12 V and Vds −30 V.
- At 1S its Vgs is only about 3 V, so Rds(on) is higher (roughly 0.1 Ω).
  At 1.2 A that's about 0.12 V and 0.15 W, which is acceptable.
- **It protects the logic only.** Motor current is several amps on 1S and
  comes from `VBAT_RAW`.

## USB power path

USB powers the logic, so the configurator and Mode B coding work without a
battery. It does this without back-feeding the LiPo.

- **VBUS feeds VBAT through Schottky D10** (B5819W, 40 V, 1 A).
- **VBUS also drives Q10's gate** through R17 (1k), against R10 (100k) to
  GND.

| Case | What happens |
|---|---|
| USB only | Q10 off. The logic runs from VBUS − Vf ≈ 4.6 V. **Motors get nothing, so USB can never spin a motor.** |
| USB + 1S (≤ 4.35 V) | Gate ≈ 4.95 V, source ≈ 4.3–4.7 V, so Vgs is +0.25 to +0.65 V and Q10 is **off**. Its body diode is reverse-biased, so **no charge current flows into the cell.** |
| USB + 2S (6–8.4 V) | The battery is higher. Q10 conducts (Vgs −1 to −3.4 V) and the pack runs the logic. D10 is reverse-biased, so nothing flows back into USB. |
| Battery only | R10 pulls the gate to GND, so Q10 is on, as before. |
| Reversed pack | Q10 is off and its body diode blocks, as before. |

**Limits:**

- **Nearly empty 2S with USB plugged in:** at about 6 V, Q10 only just turns
  on (Vgs ≈ −1 V), so it runs warm. That's harmless on the bench. Unplug USB
  or use a charged pack.
- **USB current:** a USB 2.0 port gives 500 mA.
  - Mode A (configurator) draws about 0.2 A from USB, which is fine.
  - Mode B with WiFi and the camera streaming can peak around 0.75 A. Use a
    USB-C charger or port rated above 500 mA for that.
- **Capacitance on VBUS:** the input caps (about 30 µF on VBAT) are more
  than the USB spec's 10 µF inrush limit. Most ports tolerate it. If one
  resets on plug-in, add a soft-start (load-switch) on VBUS.

## Battery voltage sense

- The 10k / 1k divider plus a 100 nF filter sits on **VBAT_RAW** (the
  battery side of Q10) and feeds STM32 **PC1**. That's Betaflight
  `vbat_scale` 110.
- Because it's on the battery side, it reads the real pack even when USB is
  plugged in, and 0 V means no battery.
- 8.4 V reads as 0.76 V and 4.2 V as 0.38 V, so the STM32 can tell a 1S
  pack from a 2S pack at boot.

## What 2S means for the motors (read this)

The power tree handles 2S. **The 716/720 brushed motors don't: they're 1S
motors.** On 2S:

- **Firmware has to cap motor output.** Betaflight `motor_output_limit`
  needs to be about 50% when a 2S pack is detected. Otherwise the motors
  see double voltage and burn.
- **The motor MOSFETs and flyback diodes must be rated ≥ 20 V.** That's
  needed for 2S anyway.
- **2S really fits the upgrade path:** 1S brushless (0802) or 2S-rated
  motors on the same frame.

## Net naming (consistent across subcircuits)

- VBAT_RAW   — battery +, before the P-FET (motors)
- VBAT       — protected battery or USB (diode-OR), feeds the buck-boost
- VBUS       — USB-C 5 V (connector in hardware/stm32), logic only
- +3V8       — TPS63070 output, feeds both LDOs
- +3V3_SYS   — STM32 + sensors (clean)
- +3V3_ESP   — ESP32-S3 + camera (isolated)
- +2V8_CAM   — camera analog (AVDD), from +3V3_ESP via XC6206P282MR (camera block)
- +1V2_CAM   — camera core (DVDD), from +3V3_ESP via XC6206P122MR (camera block)
- VBAT_SENSE — divided VBAT_RAW (real battery) to STM32 PC1
- PG_3V8     — TPS63070 power-good (open drain, 100k pull-up)
- GND        — common

## To verify before layout

- [ ] Pick a KEYED battery connector: motors sit on VBAT_RAW, so a reversed
      pack shorts through the motor FET body diodes and flyback diodes.
- [ ] Pick LCSC parts for the TPS63070RNM, the 1.5 µH inductor and the
      AO3401A, and check stock.
- [ ] Get TI's RNM0015A footprint, and follow TI's layout guidance: keep the
      VIN/VOUT caps tight to the pins and the L1/L2 loop small.
- [ ] Confirm AP7361C-33E dropout at about 600 mA leaves margin from 3.8 V.
      If not, raise Vout (R11 = 402k gives 4.02 V).
- [ ] Confirm the recommended ELRS receivers accept 3.8 V on their power pin
      (J60 is fed from +3V8; there is no 5 V rail).
- [ ] Star-ground or careful ground pour: keep ESP32 and buck-boost return
      currents from flowing under the gyro.
- [ ] Firmware: detect 1S/2S from VBAT_SENSE and set `motor_output_limit`.
- [ ] Bench-test the USB power path: USB + full 1S must show no current into
      the cell; USB + 2S must not back-feed VBUS.
