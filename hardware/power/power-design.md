# Power section — split-rail design

Status: decided (Option B, split rails). Parts to verify on LCSC before layout.

## Why split

The ESP32 draws ~120mA average in WiFi AP mode but spikes to ~500mA on TX
bursts. Combined with the STM32 + sensors + ELRS baseline (~180mA), peak demand
nears 700mA — over what a single RT9013 (500mA) can hold. A sagging rail resets
MCUs (the SIM800L brownout failure). Splitting also keeps the ESP32's noisy,
spiky load off the rail that feeds the MPU-6000 gyro, since gyro supply noise
degrades flight stability directly.

## Topology

2S LiPo (~7.4V) -> MP2307 buck -> +5V (3A) -> two independent 3.3V regulators:

- +3V3_SYS : RT9013-33 LDO. Feeds STM32F405, MPU-6000, BMP280. ~180mA. Low noise.
- +3V3_ESP : AP7361C-33 LDO (1A). Feeds ESP32 only. Isolated, spiky.

Both LDOs run from the common +5V rail. The MP2307 (3A) easily supplies both.

## Current budget

| Rail | Loads | Typical | Peak |
|---|---|---|---|
| +3V3_SYS | STM32F405, MPU-6000, BMP280, ELRS RX | ~180mA | ~230mA |
| +3V3_ESP | ESP32-WROOM-32 | ~120mA | ~500mA (TX burst) |

RT9013 (500mA) covers SYS with margin. AP7361C (1A) covers ESP peaks with margin.

## Why LDO and not buck for the ESP32 rail

For a hand-assembled kit, an LDO means no inductor and far simpler layout. The
efficiency loss (burning 1.7V as heat) is acceptable because the ESP32 only runs
in Mode B (bench/coding), not in flight, so battery runtime there barely matters.
At ~120mA average that is ~0.2W in a SOT-89/SOT-223 package — fine.
Swap to a TPS563201 buck only if Mode B runtime becomes a priority.

## Part choices (verify stock/footprint on LCSC)

| Ref | Part | Package | Note |
|---|---|---|---|
| Buck | MP2307DN | SOIC-8-EP | already in original power tree, to 5V |
| LDO (SYS) | RT9013-33GB | SOT-23-5 | low noise, 500mA |
| LDO (ESP) | AP7361C-33E | SOT-89-3 / SOT-223 | 1A, low dropout. AMS1117-3.3 = cheap fallback |

## Decoupling

- 10uF bulk at the ESP32 3V3 pin (already in the dual-boot netlist as C1 on
  +3V3_ESP). Handles the fast edge of the TX spike no regulator answers in time.
- 100nF per supply pin on both MCUs and each sensor, placed at the pin.
- Input + output caps per each regulator datasheet (typically 1uF in, 10uF out
  for the LDOs; the MP2307 needs its specified inductor + caps).

## Net naming (now consistent across subcircuits)

- +5V        — MP2307 output, feeds both LDOs
- +3V3_SYS   — STM32 + sensors (clean)
- +3V3_ESP   — ESP32 only (isolated)
- GND        — common

## To verify before layout

- [ ] Confirm AP7361C-33E (or chosen ESP LDO) stock + footprint on LCSC.
- [ ] Confirm ELRS RX supply voltage (3.3V) and put it on +3V3_SYS.
- [ ] Star-ground or careful ground pour: keep ESP32 return currents from
      flowing under the gyro. The split rails only help if the grounds are
      handled too.
