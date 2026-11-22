"""
DroneKit Pro - brushed motor driver block, as code.

Generates a KiCad-importable netlist for the four brushed-motor channels that
replace the old 4-in-1 ESC. Each channel is a low-side N-MOSFET switch driven
by plain PWM from an STM32 TIM3 pin (Betaflight brushed mode, no DSHOT):

    VBAT_RAW ---+-----------+
                |           |
              motor +     D (Schottky, cathode to VBAT_RAW)
              motor -  ---- +--- MOSFET drain
                              MOSFET source -> GND
    STM32 TIM3 -- 22R --+-- gate
                        10k pull-down to GND

Design reference: hardware/motors/motor-design.md

Decisions encoded here:
  1. Gate pull-DOWN (10k). The STM32 pins float until Betaflight starts, and
     a floating gate can turn a FET partly on: props would twitch or spin at
     power-up. The pull-down keeps every motor OFF until firmware drives it.
     Same dark-by-default rule as the ESP32-S3 EN line.
  2. A flyback Schottky across every motor. Brushed motors are inductive; at
     each PWM turn-off the motor current must keep flowing somewhere. Without
     the diode it avalanches the FET. Do NOT omit.
  3. Everything rated for 2S: AO3400A (Vds 30V) and SS34 (40V, 3A), so the
     board survives a 2S pack (8.4V) even though the 716/720 motors are 1S.
  4. Motors run from VBAT_RAW (before the reverse-polarity FET): motor
     current is several amps, far more than the logic-side AO3401A carries.
     That means a reversed battery shorts through the FET body diodes and the
     flyback diodes - use a KEYED battery connector.
  5. Bulk caps on VBAT_RAW right at the motor pads soak up PWM current spikes
     so they don't reach the buck-boost input as noise.

STM32 pins follow hardware/stm32f405-pinmap.md (all four on TIM3).
U1 here is the SAME STM32F405 as dual-boot U1; only the motor pins are listed.
Refs are PINNED in a reserved 40-59 range so this block never collides with
dual-boot (auto), power (10-29) or camera (30-39).
Run:  python3 motors.py   ->  writes motors.net + prints ERC.
"""

from skidl import Part, Pin, Net, SKIDL, KICAD8, TEMPLATE, generate_netlist, ERC, set_default_tool

set_default_tool(SKIDL)
T = Pin.types

# ----------------------------------------------------------------------------
# Passive templates + ref-pinning helpers
# ----------------------------------------------------------------------------
R = Part(name="R", tool=SKIDL, ref_prefix="R", dest=TEMPLATE,
         footprint="Resistor_SMD:R_0402_1005Metric",
         pins=[Pin(num=1, name="1", func=T.PASSIVE),
               Pin(num=2, name="2", func=T.PASSIVE)])

C = Part(name="C", tool=SKIDL, ref_prefix="C", dest=TEMPLATE,
         footprint="Capacitor_SMD:C_0805_2012Metric",
         pins=[Pin(num=1, name="1", func=T.PASSIVE),
               Pin(num=2, name="2", func=T.PASSIVE)])

def Rn(ref, value):
    p = R(value=value); p.ref = ref; return p

def Cn(ref, value):
    p = C(value=value); p.ref = ref; return p

# AO3400A N-MOSFET  SOT-23: 1 G 2 S 3 D.  30V, Vgs +/-12V, logic-level
# (specified at Vgs 2.5V, so 3.3V STM32 drive turns it fully on).
def NFET(ref):
    p = Part(name="AO3400A", tool=SKIDL, ref_prefix="Q", dest=TEMPLATE,
             pins=[Pin(num=1, name="G", func=T.PASSIVE),
                   Pin(num=2, name="S", func=T.PASSIVE),
                   Pin(num=3, name="D", func=T.PASSIVE)]
             )(value="AO3400A", footprint="Package_TO_SOT_SMD:SOT-23")
    p.ref = ref
    return p

# SS34 Schottky  SMA: 1 K  2 A.  40V, 3A - rated for motor stall current.
def SCHOTTKY(ref):
    p = Part(name="SS34", tool=SKIDL, ref_prefix="D", dest=TEMPLATE,
             pins=[Pin(num=1, name="K", func=T.PASSIVE),
                   Pin(num=2, name="A", func=T.PASSIVE)]
             )(value="SS34", footprint="Diode_SMD:D_SMA")
    p.ref = ref
    return p

# Motor solder pads: 1 = M+ (VBAT_RAW), 2 = M- (FET drain). Placeholder footprint.
def MOTOR_PADS(ref, label):
    p = Part(name="Motor_Pads", tool=SKIDL, ref_prefix="J", dest=TEMPLATE,
             pins=[Pin(num=1, name="M+", func=T.PASSIVE),
                   Pin(num=2, name="M-", func=T.PASSIVE)]
             )(value=label,
               footprint="Connector_PinHeader_1.27mm:PinHeader_1x02_P1.27mm_Vertical")
    p.ref = ref
    return p

# STM32F405 (same part as dual-boot U1) - motor PWM pins only.
# Local pin numbers, not LQFP-64 pad numbers.
MOTOR_PINS = [  # (motor, STM32 pin, timer channel)
    (1, "PB0", "TIM3_CH3"),
    (2, "PB1", "TIM3_CH4"),
    (3, "PB4", "TIM3_CH1"),
    (4, "PB5", "TIM3_CH2"),
]
stm32 = Part(name="STM32F405RGT6", tool=SKIDL, ref_prefix="U", dest=TEMPLATE,
             pins=[Pin(num=1, name="VSS", func=T.PWRIN)] +
                  [Pin(num=2 + i, name=pin, func=T.OUTPUT)
                   for i, (_, pin, _) in enumerate(MOTOR_PINS)]
             )(value="STM32F405RGT6", footprint="Package_QFP:LQFP-64_10x10mm_P0.5mm")
stm32.ref = "U1"

# ----------------------------------------------------------------------------
# Nets
# ----------------------------------------------------------------------------
vbat_raw = Net("VBAT_RAW"); vbat_raw.drive = Pin.drives.POWER   # from power block J10
gnd      = Net("GND");      gnd.drive      = Pin.drives.POWER
gnd += stm32["VSS"]

# ----------------------------------------------------------------------------
# Four identical channels
# ----------------------------------------------------------------------------
for i, (m, pin, tim) in enumerate(MOTOR_PINS):
    q  = NFET(f"Q{40 + i}")
    d  = SCHOTTKY(f"D{40 + i}")
    rg = Rn(f"R{40 + i}", "22R")          # gate series: damps ringing, limits pin current
    rp = Rn(f"R{44 + i}", "10k")          # gate pull-down: motor OFF until firmware drives it
    j  = MOTOR_PADS(f"J{40 + i}", f"M{m}")

    pwm  = Net(f"M{m}_PWM")               # STM32 TIM3 pin -> gate resistor
    gate = Net(f"M{m}_GATE")
    drn  = Net(f"M{m}_NEG")               # motor - / FET drain / diode anode

    pwm  += stm32[pin], rg[1]
    gate += rg[2], q["G"], rp[1]
    gnd  += q["S"], rp[2]
    drn  += q["D"], j["M-"], d["A"]
    vbat_raw += j["M+"], d["K"]

# ----------------------------------------------------------------------------
# Motor supply bulk: 2 x 22uF/25V on VBAT_RAW, at the motor pads
# ----------------------------------------------------------------------------
c40 = Cn("C40", "22uF/25V"); vbat_raw += c40[1]; gnd += c40[2]
c41 = Cn("C41", "22uF/25V"); vbat_raw += c41[1]; gnd += c41[2]

# ----------------------------------------------------------------------------
# Checks + output
# ----------------------------------------------------------------------------
ERC()
generate_netlist(tool=KICAD8, file_="motors.net")
print(">>> wrote motors.net")
