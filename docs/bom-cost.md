# Flight-controller BOM cost — first pass

Snapshot: 2026-11-23. Prices are LCSC listings found by web search, so they're
cached pages, not a live quote. They vary between snapshots and change often;
**re-check on lcsc.com before ordering**. All prices are USD per board at about
the **100+ price tier**, which matches a small kit run assembled by JLCPCB.

Scope: the **flight-controller PCB only** (`hardware/board/board.net`: 57 line
items, 155 parts). Not included: PCB fabrication and assembly fees (estimated
separately below), the motors, props, battery, camera module, printed cage,
or the optional ELRS receiver.

## Headline

| Configuration | Parts per board |
|---|---|
| Original design (ICM-42688-P + BMP280, both from LCSC) | ≈ $39 |
| **Current design: baro swapped to the SPA06-003 (done 2026-11-23)** | **≈ $29** |
| ...and source the ICM-42688-P at about $5 (not via LCSC) | ≈ $17 |

**Two sensors were ~70% of the cost**, and both had problems at LCSC. The baro
is now fixed in the design (`hardware/baro/`); the gyro is still open:

1. **BMP280 barometer: discontinued at LCSC. Done: replaced with the
   SPA06-003.** Its page lists it as
   discontinued, with 0–2 in stock, at about $10.6. It can't be planned on.
   - **Recommended replacement: Goertek SPA06-003**, about $0.43, with
     36k–72k in stock.
   - Betaflight supports it: its DPS310 driver covers the DPS310, DPS368,
     SPL07-003 and SPA06-003.
   - Avoid the DPS310 itself, which is obsolete per DigiKey.
   - Avoid the SPL06-001: it's in stock, but it's not in Betaflight's
     supported-sensor table.
2. **ICM-42688-P gyro: about $16.3 at LCSC.** DigiKey lists the same part
   at about $4.9 for one, falling to $3.3 at 1k, but it was out of stock.
   - JLCPCB assembly uses LCSC stock, so a JLC-assembled board pays about $16.
   - Options:
     1. **Pay the $16** for simplicity.
     2. **Buy elsewhere and consign** the parts to JLCPCB, or use JLC's
        global-sourcing service.
     3. **Change the gyro.**
        - The ICM-42605 is about $8.4 at LCSC and is in Betaflight's
          supported list.
        - The BMI270 is about $1.2–1.7, but Betaflight marks it "not
          recommended": uncalibrated gyro, 3.2 kHz maximum rate.

## Line items

### ICs and modules

| Ref | Part | LCSC | Qty | Unit ≈ | Line ≈ | Stock / note |
|---|---|---|---|---|---|---|
| U1 | STM32F405RGT6 (TR reel C2054141 when C15742 is out of stock) | C15742 | 1 | 4.51–5.05 | 5.00 | ~1.8k–3k; several snapshots |
| U2 | ESP32-S3-WROOM-1-N8R2 | C2913204 | 1 | 2.99–3.16 | 3.00 | ~2.8k–9.4k |
| U80 | ICM-42688-P | C1850418 | 1 | 16.30 | 16.30 | ~3.1k–6.2k. **Cost driver**, see above |
| U70 | SPA06-003 (Goertek) | C30589048 | 1 | 0.43 | 0.43 | ~36k–72k. Replaces the BMP280 (C83291: discontinued, ~$10.59) |
| U10 | TPS63070RNMR | C109322 | 1 | 0.87 | 0.87 | ~20.6k |
| U92 | TS3USB221ARSER | C128396 | 1 | 0.26 | 0.26 | ~59k. Make sure it's TI's part, not the HXY clone |
| U12 | AP7361C-33E-13 | C500795 | 1 | 0.41 | 0.41 | ~1k–3.7k |
| U11 | RT9013-33GB | C47773 | 1 | 0.13 | 0.13 | 127k+ |
| U30 | XC6206P282MR (UMW) | C347374 | 1 | 0.02 | 0.02 | 600k |
| U31 | XC6206P122MR(1uA) (TECH PUBLIC) | C2827649 | 1 | 0.09 | 0.09 | ~6.3k. Avoid the Torex "-G" C424699 (60 mA) |
| U91 | USBLC6-2SC6 | C7519 | 1 | 0.08 | 0.08 | ~40k |

### Discretes and connectors

| Ref | Part | LCSC | Qty | Unit ≈ | Line ≈ | Note |
|---|---|---|---|---|---|---|
| Q40–43, Q120 | AO3400A | C20917 | 5 | 0.046 | 0.23 | 500k+ |
| Q10 | AO3401A | C15127 | 1 | 0.046 | 0.05 | 600k+ |
| D40–43 | SS34 | C8678 | 4 | 0.035 | 0.14 | 2.9M |
| D10, D120 | B5819W | C8598 | 2 | 0.016 | 0.03 | 223k |
| J90 | USB-C TYPE-C-31-M-12 | C165948 | 1 | 0.17 | 0.17 | 200k |
| J30 | 24-pin 0.5 mm flip FPC, e.g. AFC01-S24FCC-00 | C262276 | 1 | 0.07 | 0.07 | ~4k. Pick one whose contact side matches the camera ribbon |
| J130, J131, J134 | JST SH 4-pin SM04B-SRSS-TB | C160404 | 3 | 0.13 | 0.38 | ~36k |
| J133, J135 | JST SH 6-pin | — | 2 | ~0.15 | 0.30 | estimate |
| J132 | JST SH 3-pin | — | 1 | ~0.12 | 0.12 | estimate |
| L10 | 1.5 µH shielded, Isat ≥ 2 A | — | 1 | ~0.15 | 0.15 | estimate. The Coilcraft XFL4020 isn't at LCSC, so pick an LCSC equivalent |
| Y90 | 8 MHz 3225, CL = 20 pF | — | 1 | ~0.05 | 0.05 | estimate |
| SW1, SW2, SW90 | Copal CHS-01A 1-position slide + 2 × C&K KMR2 tactile (4.2 × 2.8 mm) | — | 3 | ~0.05 | 0.15 | estimate |
| D90 | LED 0402 | — | 1 | 0.01 | 0.01 | basic part |
| C*, R* | ~95 passives, 0402/0603/0805 | basic | ~95 | ~0.003 | 0.30 | estimate |

Solder-pad "connectors" (battery, motors, receiver, buzzer, SWD, UART0)
are PCB pads and cost nothing.

### Total (parts only, about 100+ tier)

| | ≈ USD |
|---|---|
| Original design (BMP280) | 38.9 |
| **Current design (SPA06-003)** | **28.7** |
| + ICM-42688-P at about $5 (consigned or other source) | 17.4 |
| + BMI270 instead (not recommended by Betaflight) | 13.6 |

## PCB fabrication and assembly (rough estimate, not quoted)

- **PCB:** 4-layer, 32 × 30 mm. JLCPCB's small 4-layer boards are
  typically a few dollars per 5–10 boards.
- **Assembly:** parts sit on **both sides** (the ESP32-S3 on top, the rest
  underneath), which means JLCPCB's standard (not economic) assembly, with
  setup charged per side.
- **Extended-part fees:** JLCPCB charges a loading fee for each unique
  "extended" (non-basic) part. Roughly 15 of this board's parts are likely
  extended: the MCUs, sensors, TPS63070, USB switch, LDOs, connectors and
  inductor. That's a fixed cost per order, not per board.
- **The rule of thumb:** fixed costs (setup, extended fees, stencil) add
  roughly **$10+ per board at 10 boards**, falling to **about $1–2 per board
  at 100**. Get a real quote by uploading the BOM and placement file once
  layout exists.

## What this means for the design

1. **Done: the baro is now the SPA06-003.** That saves about $10 per board
   and drops a discontinued part. The Goertek datasheet (Ver 2.0) confirms
   the same pinout as the BMP280 and address 0x76 with SDO to GND. Its
   pull-ups moved from 4.7k to 5.1k, the datasheet's 5k minimum.
2. **Decide how to source the gyro** (see above). Keep the ICM-42688-P
   footprint either way; the ICM-42605 is a different part, so check its
   pinout before treating it as an alternative.
3. **The board is now about $17–29 in parts**, before
   assembly. Add the motors, battery, camera, props and printed cage for
   the kit price. Those aren't priced here.

## Sources (cached LCSC and distributor pages, 2026-11-23)

[STM32F405RGT6](https://www.lcsc.com/product-detail/C15742.html) ·
[ESP32-S3-WROOM-1-N8R2](https://www.lcsc.com/product-detail/C2913204.html) ·
[ICM-42688-P](https://www.lcsc.com/product-detail/Attitude-Sensors-Gyroscope_TDK-InvenSense-ICM-42688-P_C1850418.html) ·
[ICM-42688-P at DigiKey](https://www.digikey.com/en/products/detail/tdk-invensense/ICM-42688-P/10824934) ·
[BMP280](https://www.lcsc.com/product-detail/C83291.html) ·
[SPA06-003](https://www.lcsc.com/product-detail/C30589048.html) ·
[DPS310 (DigiKey: obsolete)](https://www.digikey.com/en/products/detail/infineon-technologies/DPS310XTSA1/6565756) ·
[SPL06-001](https://www.lcsc.com/product-detail/C2684428.html) ·
[BMI270](https://www.lcsc.com/product-detail/C2836813.html) ·
[ICM-42605](https://www.lcsc.com/product-detail/C2655099.html) ·
[Betaflight supported sensors](https://betaflight.com/docs/wiki/guides/current/Supported-Sensors) ·
[TPS63070RNMR](https://www.lcsc.com/product-detail/DC-DC-Converters_TI_TPS63070RNMR_TPS63070RNMR_C109322.html) ·
[TS3USB221ARSER](https://www.lcsc.com/product-detail/Analog-Switches-Special-Purpose_Texas-Instruments-TS3USB221ARSER_C128396.html) ·
[RT9013-33GB](https://www.lcsc.com/product-detail/C47773.html) ·
[AP7361C-33E-13](https://www.lcsc.com/product-detail/C500795.html) ·
[XC6206P282MR](https://www.lcsc.com/product-detail/Low-Dropout-Regulators-LDO_Youtai-Semiconductor-Co-Ltd-XC6206P282MR_C347374.html) ·
[XC6206P122MR](https://www.lcsc.com/product-detail/C2827649.html) ·
[USBLC6-2SC6](https://www.lcsc.com/product-detail/C7519.html) ·
[AO3400A](https://www.lcsc.com/product-detail/C20917.html) ·
[SS34](https://www.lcsc.com/product-detail/C8678.html) ·
[B5819W](https://www.lcsc.com/product-detail/Schottky-Barrier-Diodes-SBD_Jiangsu-Changjing-Electronics-Technology-Co-Ltd-B5819W-SL_C8598.html) ·
[TYPE-C-31-M-12](https://www.lcsc.com/product-detail/C165948.html) ·
[AFC01-S24FCC-00](https://www.lcsc.com/product-detail/C262276.html) ·
[SM04B-SRSS-TB](https://www.lcsc.com/product-detail/C160404.html)
