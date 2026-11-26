"""
DroneKit Pro - thrust-to-weight and flight-time estimate (1S brushed whoop).

A first-order model, not a substitute for a bench test. It uses:

  * Momentum (actuator-disk) theory for the power to make thrust T with
    4 open props of diameter D:   P_ideal = T^1.5 / sqrt(2 * rho * A_total)
  * An overall electrical->thrust efficiency (motor x prop) taken from bench
    data on tiny brushed whoop motors (mshtools 2018: ~0.22-0.24 total for
    16.4-17.5 kV 0615/0716 motors on 30 mm props).
  * A real-world derating factor calibrated so the model reproduces a real
    quad with the SAME layout as DroneKit: BetaFPV Beta75 (7x20 mm 17500 kV
    brushed motors, 40 mm props, 75 mm frame): 32 g dry + 260 mAh pack,
    3 min 30 s stated flight time.

Run:  python3 thrust_weight.py
Edit the WEIGHTS / SCENARIOS tables to try changes.
"""

from math import pi, sqrt

G = 9.81
RHO = 1.2                 # air density, kg/m^3
PROP_D = 0.040            # 40 mm props (DroneKit Cage prop_d)
N_PROPS = 4
ETA_TOTAL = 0.22          # electrical power -> ideal induced power (motor x prop)
V_AVG = 3.7               # average 1S voltage under load
USABLE = 0.80             # fraction of rated mAh used before landing

# Max electrical power per 7x20 brushed motor at full throttle on 1S.
# No bench data was found for 720 + 40 mm props, so this is a RANGE:
# ~2-2.7 A at ~3.5 V under load. Stall is far higher (one 720 datasheet:
# 6.7 A at 3 V), but props unload the motor well below stall.
P_MAX_PER_MOTOR = {"low": 6.0, "mid": 8.0, "high": 10.0}   # W


def area_total():
    return N_PROPS * pi * (PROP_D / 2) ** 2


def ideal_power(thrust_n):
    return thrust_n ** 1.5 / sqrt(2 * RHO * area_total())


def hover_power_w(auw_g):
    """Electrical power to hover at all-up weight auw_g (grams)."""
    return ideal_power(auw_g / 1000 * G) / ETA_TOTAL


def max_thrust_g(p_elec_per_motor):
    """Total static thrust (grams) at a given electrical power per motor."""
    p_ideal_total = N_PROPS * p_elec_per_motor * ETA_TOTAL
    t_n = (p_ideal_total * sqrt(2 * RHO * area_total())) ** (2 / 3)
    return t_n / G * 1000


def ideal_minutes(auw_g, mah):
    amps = hover_power_w(auw_g) / V_AVG
    return mah / 1000 * USABLE / amps * 60


# --- calibration on the BetaFPV Beta75 -----------------------------------
BETA75_DRY, BETA75_BATT_MAH, BETA75_BATT_G, BETA75_MIN = 32.0, 260, 7.0, 3.5
DERATE = BETA75_MIN / ideal_minutes(BETA75_DRY + BETA75_BATT_G, BETA75_BATT_MAH)

# --- DroneKit weight build-up (grams) --------------------------------------
# source tags: [F] Fusion model, [D] datasheet/listing, [E] estimate
WEIGHTS = {
    "cage (PLA, 108x108x34, 85 mm wb)": (10.3, "[F] DroneKit Cage 8.27 cm3 x 1.24 g/cm3 (1.5 mm pods, 3 mm arms, 2 mm battery holder under the plate)"),
    "FC PCB 32x30x0.8 mm, 4-layer":     (1.5,  "[E] FR4 volume x ~1.9 g/cm3 (was 1.6 mm, 2.9 g)"),
    "vision PCB 32x30x1.0 mm, 4-layer": (1.8,  "[E] FR4 volume x ~1.9 g/cm3 (second board of the stack)"),
    "B2B header + socket, 4 standoffs": (0.8,  "[E] 2x12 1.27 mm pair + M1.4 nylon spacers"),
    "ESP32-S3-WROOM-1 module":          (3.0,  "[E] 18x25.5x3.1 mm shielded module"),
    "other FC parts + 6 JST-SH + USB-C": (2.5, "[E] STM32, regulators, connectors"),
    "4x 7x20 motors (17500 kV)":        (14.0, "[D] BetaFPV 7x20: ~3.5 g each (generic 720: up to ~5 g)"),
    "4x 40 mm 4-blade props":           (1.4,  "[E] ~0.35 g each"),
    "camera module (OV2640 + FPC)":     (1.5,  "[E]"),
    "wiring, screws, foam":             (1.5,  "[E]"),
}
BATTERIES = {450: (12.7, "[D] BetaFPV 1S 450 mAh BT2.0"),
             300: (8.3,  "[D] BetaFPV 1S 300 mAh BT2.0")}

DRY = sum(w for w, _ in WEIGHTS.values())

SCENARIOS = [
    # name, dry weight change (g), battery mAh
    ("Current design, 450 mAh",                       0.0, 450),
    ("Current design, 300 mAh",                       0.0, 300),
    ("1.6 mm FC PCB instead (+1.4 g), 300 mAh",       +1.4, 300),
    ("BetaFPV Beta75 reference (32 g dry, 260 mAh)", 32.0 - DRY - 7.0 + 7.0, 260),
]


def main():
    print("Weight build-up")
    for name, (w, src) in WEIGHTS.items():
        print(f"  {name:36} {w:5.1f} g  {src}")
    print(f"  {'DRY (no battery)':36} {DRY:5.1f} g")
    for mah, (w, src) in BATTERIES.items():
        print(f"  + {mah} mAh battery {w:5.1f} g  {src}  -> AUW {DRY + w:5.1f} g")
    print()
    print(f"Calibration: Beta75 model/real flight-time factor = {DERATE:.2f}")
    t_lo, t_mid, t_hi = (max_thrust_g(P_MAX_PER_MOTOR[k]) for k in ("low", "mid", "high"))
    print(f"Max total thrust, 4x 720 + 40 mm: {t_lo:.0f} / {t_mid:.0f} / {t_hi:.0f} g "
          f"(at {P_MAX_PER_MOTOR['low']:.0f} / {P_MAX_PER_MOTOR['mid']:.0f} / "
          f"{P_MAX_PER_MOTOR['high']:.0f} W per motor)")
    print()
    print(f"{'Scenario':47} {'AUW':>6} {'T/W (low-mid-high)':>20} {'hover A':>8} {'flight':>8}")
    for name, delta, mah in SCENARIOS:
        if name.startswith("BetaFPV"):
            auw = BETA75_DRY + BETA75_BATT_G
        else:
            auw = DRY + delta + BATTERIES[mah][0]
        tw = "-".join(f"{t / auw:.1f}" for t in (t_lo, t_mid, t_hi))
        amps = hover_power_w(auw) / V_AVG
        mins = ideal_minutes(auw, mah) * DERATE
        print(f"{name:47} {auw:5.1f}g {tw:>20} {amps:7.1f}A {mins:6.1f}min")


if __name__ == "__main__":
    main()
