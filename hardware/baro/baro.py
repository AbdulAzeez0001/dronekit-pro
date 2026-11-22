"""
DroneKit Pro - BMP280 barometer block, as code.

Generates a KiCad-importable netlist for the BMP280 pressure sensor on the
STM32's I2C1 (Betaflight: baro altitude hold / altitude in OSD; ESP32 side
gets it over MSP for "hold altitude" in student code).

    +3V3_SYS --> U70 BMP280 (VDD + VDDIO, 100nF each)
    STM32 PB6 (I2C1_SCL) <--> SCK
    STM32 PB7 (I2C1_SDA) <--> SDI
    CSB -> VDDIO (selects I2C)   SDO -> GND (address 0x76)

Design reference: hardware/baro/baro-design.md

Decisions encoded here:
  1. I2C, not SPI. The baro is slow (tens of Hz), and I2C1 keeps SPI1 for
     the gyro alone. CSB must be tied HIGH at power-up: if it ever sees a
     low edge, the BMP280 locks into SPI mode until the next power cycle.
  2. Address 0x76 (SDO to GND), Betaflight's default BMP280 address.
  3. On +3V3_SYS, the clean rail: pressure readings pick up supply noise.
  4. The 4.7k I2C pull-ups live here, so the bus works with only the baro on
     it. I2C1 also goes to the expansion header for add-on I2C sensors
     (e.g. a ToF board); add-on boards must NOT add their own pull-ups, or
     drop to one set if they do.

Pinout (Bosch BMP280 datasheet, 8-pin LGA 2.0 x 2.5 mm, bottom view):
  1 GND  2 CSB  3 SDI  4 SCK  5 SDO  6 VDDIO  7 GND  8 VDD

U1 here is the SAME STM32F405 as dual-boot U1; only these pins are listed.
Refs are PINNED in a reserved 70-79 range so this block never collides with
dual-boot (auto), power (10-29), camera (30-39), motors (40-59) or the
receiver port (60-69).
Run:  python3 baro.py   ->  writes baro.net + prints ERC.
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
         footprint="Capacitor_SMD:C_0402_1005Metric",
         pins=[Pin(num=1, name="1", func=T.PASSIVE),
               Pin(num=2, name="2", func=T.PASSIVE)])

def Rn(ref, value):
    p = R(value=value); p.ref = ref; return p

def Cn(ref, value):
    p = C(value=value); p.ref = ref; return p

# ----------------------------------------------------------------------------
# BMP280, LGA-8 (Bosch datasheet pin numbers)
# ----------------------------------------------------------------------------
u70 = Part(name="BMP280", tool=SKIDL, ref_prefix="U", dest=TEMPLATE,
           pins=[Pin(num=1, name="GND",   func=T.PWRIN),
                 Pin(num=2, name="CSB",   func=T.INPUT),
                 Pin(num=3, name="SDI",   func=T.BIDIR),   # I2C SDA
                 Pin(num=4, name="SCK",   func=T.INPUT),   # I2C SCL
                 Pin(num=5, name="SDO",   func=T.INPUT),   # I2C address LSB
                 Pin(num=6, name="VDDIO", func=T.PWRIN),
                 Pin(num=7, name="GND_7", func=T.PASSIVE),
                 Pin(num=8, name="VDD",   func=T.PWRIN)]
           )(value="BMP280",
             footprint="Package_LGA:Bosch_LGA-8_2x2.5mm_P0.65mm_ClockwisePinNumbering")
u70.ref = "U70"

# STM32F405 (same part as dual-boot U1) - I2C1 only. Local pin numbers.
stm32 = Part(name="STM32F405RGT6", tool=SKIDL, ref_prefix="U", dest=TEMPLATE,
             pins=[Pin(num=1, name="VSS", func=T.PWRIN),
                   Pin(num=2, name="PB6", func=T.OUTPUT),   # I2C1_SCL
                   Pin(num=3, name="PB7", func=T.BIDIR)]    # I2C1_SDA
             )(value="STM32F405RGT6", footprint="Package_QFP:LQFP-64_10x10mm_P0.5mm")
stm32.ref = "U1"

# ----------------------------------------------------------------------------
# Nets
# ----------------------------------------------------------------------------
v3v3_sys = Net("+3V3_SYS"); v3v3_sys.drive = Pin.drives.POWER   # from power block (RT9013)
gnd      = Net("GND");      gnd.drive      = Pin.drives.POWER
gnd += stm32["VSS"]

# Supply: VDD and VDDIO both on the clean rail, 100nF each at the pins
v3v3_sys += u70["VDD"], u70["VDDIO"]
gnd      += u70["GND"], u70["GND_7"]
c70 = Cn("C70", "100nF"); v3v3_sys += c70[1]; gnd += c70[2]   # VDD
c71 = Cn("C71", "100nF"); v3v3_sys += c71[1]; gnd += c71[2]   # VDDIO

# Interface select + address
v3v3_sys += u70["CSB"]            # CSB high = I2C (must never see a low edge)
gnd      += u70["SDO"]            # SDO low  = address 0x76

# I2C1 + pull-ups (the bus's only pull-ups; shared with the expansion header)
scl = Net("I2C1_SCL"); scl += stm32["PB6"], u70["SCK"]
sda = Net("I2C1_SDA"); sda += stm32["PB7"], u70["SDI"]
r70 = Rn("R70", "4.7k"); scl += r70[1]; v3v3_sys += r70[2]
r71 = Rn("R71", "4.7k"); sda += r71[1]; v3v3_sys += r71[2]

# ----------------------------------------------------------------------------
# Checks + output
# ----------------------------------------------------------------------------
ERC()
generate_netlist(tool=KICAD8, file_="baro.net")
print(">>> wrote baro.net")
