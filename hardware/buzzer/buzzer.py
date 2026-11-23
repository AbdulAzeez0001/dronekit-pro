"""
DroneKit Pro - buzzer (beeper) block, as code.

Generates a KiCad-importable netlist for Betaflight's beeper: a low-side
N-MOSFET on STM32 PB8 switching an external buzzer soldered to two pads.
Used for arming/disarming beeps, low-battery warnings and the lost-model
alarm (find the whoop after it crashes under a sofa).

    +3V8 --- J120 BZ+  [ buzzer ]  BZ- --- Q120 drain
                                           Q120 source -> GND
    D120 Schottky across the buzzer (cathode to +3V8)
    STM32 PB8 -- 22R --+-- Q120 gate
                       10k pull-down to GND

Design reference: hardware/buzzer/buzzer-design.md

Decisions encoded here:
  1. Pads for an external buzzer, not an onboard one. A loud buzzer is 9-12 mm
     across, too big for the 32 x 30 mm board, and some builders skip it.
     Any small "active" 3-5V buzzer works (it beeps by itself when powered).
  2. Powered from +3V8, not VBAT: on 2S, VBAT reaches 8.4V, too much for a
     5V buzzer. There is no 5V rail; a 5V-rated active buzzer at 3.8V is a
     little quieter but works. Never from +3V3_SYS (keeps its current spikes
     off the gyro rail).
  3. Same FET and diode parts as the motor drivers (AO3400A) and the USB
     path (B5819W) - fewer different parts on the BOM.
  4. Gate pull-down: silent while the STM32 boots.
  5. Flyback Schottky across the pads: magnetic buzzers are inductive.

U1 here is the SAME STM32F405 as the stm32 block's U1; only PB8 is listed.
Refs are PINNED in a reserved 120-129 range so this block never collides with
any other block (STM32 block uses 90-119).
Run:  python3 buzzer.py   ->  writes buzzer.net + prints ERC.
"""

from skidl import Part, Pin, Net, SKIDL, KICAD8, TEMPLATE, generate_netlist, ERC, set_default_tool

set_default_tool(SKIDL)
T = Pin.types

R = Part(name="R", tool=SKIDL, ref_prefix="R", dest=TEMPLATE,
         footprint="Resistor_SMD:R_0402_1005Metric",
         pins=[Pin(num=1, name="1", func=T.PASSIVE),
               Pin(num=2, name="2", func=T.PASSIVE)])

C = Part(name="C", tool=SKIDL, ref_prefix="C", dest=TEMPLATE,
         footprint="Capacitor_SMD:C_0402_1005Metric",
         pins=[Pin(num=1, name="1", func=T.PASSIVE),
               Pin(num=2, name="2", func=T.PASSIVE)])

def Rn(ref, value):
    p = R(value=value); p.ref = ref; return p

def Cn(ref, value):
    p = C(value=value); p.ref = ref; return p

# AO3400A N-MOSFET  SOT-23: 1 G 2 S 3 D (same part as the motor drivers)
q120 = Part(name="AO3400A", tool=SKIDL, ref_prefix="Q", dest=TEMPLATE,
            pins=[Pin(num=1, name="G", func=T.PASSIVE),
                  Pin(num=2, name="S", func=T.PASSIVE),
                  Pin(num=3, name="D", func=T.PASSIVE)]
            )(value="AO3400A", footprint="Package_TO_SOT_SMD:SOT-23")
q120.ref = "Q120"

# B5819W Schottky  SOD-123: 1 K  2 A (same part as the USB power path)
d120 = Part(name="B5819W", tool=SKIDL, ref_prefix="D", dest=TEMPLATE,
            pins=[Pin(num=1, name="K", func=T.PASSIVE),
                  Pin(num=2, name="A", func=T.PASSIVE)]
            )(value="B5819W", footprint="Diode_SMD:D_SOD-123")
d120.ref = "D120"

# Buzzer pads: 1 BZ+  2 BZ-
j120 = Part(name="Buzzer_Pads", tool=SKIDL, ref_prefix="J", dest=TEMPLATE,
            pins=[Pin(num=1, name="BZ+", func=T.PASSIVE),
                  Pin(num=2, name="BZ-", func=T.PASSIVE)]
            )(value="BUZZER", footprint="Connector_PinHeader_1.27mm:PinHeader_1x02_P1.27mm_Vertical")
j120.ref = "J120"

# STM32F405 (same part as the stm32 block's U1) - PB8 only. Local pin numbers.
stm32 = Part(name="STM32F405RGT6", tool=SKIDL, ref_prefix="U", dest=TEMPLATE,
             pins=[Pin(num=1, name="VSS", func=T.PWRIN),
                   Pin(num=2, name="PB8", func=T.OUTPUT)]
             )(value="STM32F405RGT6", footprint="Package_QFP:LQFP-64_10x10mm_P0.5mm")
stm32.ref = "U1"

# ----------------------------------------------------------------------------
# Nets
# ----------------------------------------------------------------------------
v3v8 = Net("+3V8"); v3v8.drive = Pin.drives.POWER   # from power block (TPS63070)
gnd  = Net("GND");  gnd.drive  = Pin.drives.POWER
gnd += stm32["VSS"]

beeper = Net("BEEPER")                               # STM32 PB8
gate   = Net("BZ_GATE")
bz_neg = Net("BZ_NEG")

r120 = Rn("R120", "22R")                             # gate series
r121 = Rn("R121", "10k")                             # gate pull-down: silent at boot
beeper += stm32["PB8"], r120[1]
gate   += r120[2], q120["G"], r121[1]
gnd    += q120["S"], r121[2]

v3v8   += j120["BZ+"], d120["K"]
bz_neg += j120["BZ-"], q120["D"], d120["A"]

c120 = Cn("C120", "1uF")                             # local decoupling at the pads
v3v8 += c120[1]; gnd += c120[2]

ERC()
generate_netlist(tool=KICAD8, file_="buzzer.net")
print(">>> wrote buzzer.net")
