# Shopping list: motors, props, batteries

Date: 2026-11-26. Motors are **8×20** since 2026-11-26. Specs come from `simulation/thrust-weight.md` and
`hardware/motors/motor-design.md`. Prices are rough ranges, not quotes;
check the shop before buying.

Buy it in two steps. Step 1 is cheap and tells us whether the motors are
strong enough before you spend on the rest.

## Step 1: one-motor thrust test (about $10–20)

| # | Item | Spec to look for | Qty | Rough price |
|---|---|---|---|---|
| 1 | 8×20 brushed coreless motor | **8 mm** × 20 mm (not 8.5), 1S, 1 mm shaft, about 15,000 kV, which is **about 55,000 RPM no-load at 3.7 V**. About 3.5 g. BetaFPV's "8x20mm 15000KV" is the reference. Generic "0720"/"8520" toy motors listed at 37,000–45,000 RPM are built for 55 mm props and too slow here. | 1 set (2 CW + 2 CCW) | $6–16 |
| 2 | 40 mm prop | 40 mm, **1.0 mm shaft** | 1 set | $2–4 |
| 3 | 1S LiPo, 300 mAh | 1S, 300 mAh, 30C or more, **BT2.0** connector, about 8–9 g | 1 | $4–6 |
| 4 | 1S charger | USB, 1S, with a **BT2.0** port | 1 | $5–10 |
| 5 | BT2.0 pigtail | BT2.0 plug with short wires, to connect the motor to the battery for the test | 1 | $1–3 |
| 6 | Kitchen scale | reads to 0.1 g (a "jewellery" or "pocket" scale) | 1 | $5–10, or borrow one |

Already have or can improvise: a small block to mount the motor on, tape or
a zip tie, and a multimeter if you want to read current.

**The test** (full steps in `simulation/thrust-weight.md`): mount the motor
on the scale with the prop blowing **up**, tare, connect the battery for a
few seconds, read the grams. A brushed motor runs at full power straight
off the battery, so no controller is needed. Keep fingers clear of the prop.

- **25 g or more per motor:** the current design works. Go to step 2.
- **20–25 g:** marginal. Lighten the cage first.
- **Under 20 g:** lighten the cage first; past that, 1S brushless is the
  next step.

## Step 2: the full drone set (about $30–50 more)

| # | Item | Spec | Qty | Rough price |
|---|---|---|---|---|
| 1 | 8×20 motors | same as step 1 | the step-1 set covers the drone; buy 1 spare set | $6–16 |
| 2 | 40 mm props | same as step 1 | 2–3 sets (they break) | $4–8 |
| 3 | 1S LiPo, 300 mAh | same as step 1 | 3–4 packs in total | $12–20 |
| 4 | Multi-port 1S charger | BT2.0, charges 4–6 packs at once | 1 (optional; replaces the single one) | $10–15 |

## Listings checked (2026-11-26)

Stock and prices change; check before buying. Shipping LiPo batteries by
air is often restricted, so buy the batteries from a shop that ships to you
by ground or locally if you can.

| Item | Listing | Key specs | Notes |
|---|---|---|---|
| **8×20 motors (the design)** | [BetaFPV 8x20mm 15000KV (2CW+2CCW)](https://betafpv.com/products/8x20mm-14000kv-brushed-motors-2cw-2ccw) | 8 × 20 mm, 1 mm shaft, about 3.5 g, 56,000 RPM at 3.7 V, 1.25 mm JST plug | Pick the 15000 KV version, not the Inductrix 14000 KV one. Not the 8.5×20. Some listings disagree on whether the pack has CW, CCW or both; check before ordering |
| 7×20 motors (old choice; needs `motor_d` back to 7) | [BetaFPV 7x20mm 17500KV (2CW+2CCW)](https://betafpv.com/products/7x20mm-coreless-brushed-motors-for-beta75) | 7 × 20 mm, 1 mm shaft, about 3.5 g, 60,000–65,000 RPM | Some shops list it as discontinued |
| 40 mm props | [BetaFPV 40mm 4-blade, 1.0 mm shaft (GetFPV)](https://www.getfpv.com/betafpv-40mm-4-blade-whoop-propellers-1-0mm-shaft.html) | 40 mm, 1.0 mm shaft | Fits both motors above |
| 300 mAh batteries | [BetaFPV BT2.0 300mAh 1S 30C (8 pcs)](https://betafpv.com/products/bt2-0-300mah-1s-30c-battery-8pcs) | 300 mAh, 30C (60C burst), 67.3 × 11.8 × 6.1 mm, 8.3 g, BT2.0 | Comes with a BT2.0-to-PH2.0 charging adapter |

The motors come with a 1.25 mm JST plug. The board has solder pads, so cut
the plug off and solder the wires.

## Must-haves when choosing

- **Every battery and the charger use BT2.0.** It's keyed, so a pack can't
  go in backwards. That matters: the motors run straight off the battery,
  and a reversed pack would short through the board.
- **Motors come in CW and CCW.** The drone needs two of each. They're
  usually marked by wire colour (red/blue vs black/white).
- **Props must fit the motor shaft.** Buy them from the same shop as the
  motors, or check both listings give the same shaft size.
- **Battery size:** BetaFPV's BT2.0 300 mAh is 67.3 × 11.8 × 6.1 mm and
  8.3 g. The cage's holder is sized for exactly this pack (12.5 × 6.5 mm
  opening). Another brand's 300 mAh pack may be wider or thicker; check it
  against that before buying.
- **Avoid 450 mAh packs for now.** They add 4.4 g and lower thrust/weight
  for only about a minute more flight.

## Battery safety

- Charge on a non-flammable surface and don't leave it unattended.
- Don't run a pack below about 3.3 V, and stop using any pack that puffs up.
- Store at about 3.8 V if you won't fly for a week or more.
