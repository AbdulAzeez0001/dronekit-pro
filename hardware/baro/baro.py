"""
DroneKit Pro - SPA06-003 barometer block, as code.

Generates a KiCad-importable netlist for the Goertek SPA06-003 pressure
sensor on the
STM32's I2C1 (Betaflight: baro altitude hold / altitude in OSD; ESP32 side
gets it over MSP for "hold altitude" in student code).

    +3V3_SYS --> U70 SPA06-003 (VDD + VDDIO, 100nF each)
    STM32 PB6 (I2C1_SCL) <--> SCK
    STM32 PB7 (I2C1_SDA) <--> SDA
    CSB -> VDDIO (selects I2C)   SDO -> GND (address 0x76)

Design reference: hardware/baro/baro-design.md

Replaces the BMP280, which LCSC lists as discontinued (see docs/bom-cost.md).
Betaflight reads the SPA06-003 with its DPS310 driver (covers DPS310, DPS368,
SPL07-003, SPA06-003).

Values and pins from the Goertek SPA06-003 datasheet (Ver 2.0, 2023-12-05):
  Table 11 pin configuration (LGA-8, 2.0 x 2.5 x 0.95 mm):
    1 GND  2 CSB  3 SDA  4 SCK  5 SDO  6 VDDIO  7 GND  8 VDD
    I2C mode: CSB "not used (open) or tie to VDDIO"; SDO = address LSB.
  Address: 0x77 by default, 0x76 with SDO pulled to GND (section 6, I2C).
  Table 6 component values: pull-ups 5k-100k; supply caps C1, C2 = 100nF,
    as close to the package pins as possible.
  Supply: VDD 1.7-3.6V, VDDIO 1.08-3.6V.
  The pinout matches the BMP280's pin for pin, so the swap is the part, the
  value and the pull-ups.

Decisions encoded here:
  1. I2C, not SPI. The baro is slow (tens of Hz), and I2C1 keeps SPI1 for
     the gyro alone. CSB tied to VDDIO (allowed by Table 11) so the part can
     never drop into SPI mode.
  2. Address 0x76 (SDO to GND). Check Betaflight's DPS310 driver probes it,
     or set baro_i2c_address.
  3. On +3V3_SYS, the clean rail: pressure readings pick up supply noise.
  4. The I2C pull-ups live here, 5.1k (Table 6 minimum is 5k; the BMP280
     design's 4.7k was below it), so the bus works with only the baro on it.
     I2C1 also goes to the expansion header for add-on I2C sensors (e.g. a
     ToF board); add-on boards must NOT add their own pull-ups, or drop to
     one set if they do.

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
# SPA06-003, LGA-8 (Goertek datasheet Table 11 pin numbers)
# Footprint: same 2.0 x 2.5 mm, 0.65 mm-pitch LGA-8 as the BMP280; check the
# land pattern against the Goertek outline drawing (section 8.2) before layout.
# ----------------------------------------------------------------------------
u70 = Part(name="SPA06-003", tool=SKIDL, ref_prefix="U", dest=TEMPLATE,
           pins=[Pin(num=1, name="GND",   func=T.PWRIN),
                 Pin(num=2, name="CSB",   func=T.INPUT),
                 Pin(num=3, name="SDA",   func=T.BIDIR),   # I2C SDA
                 Pin(num=4, name="SCK",   func=T.INPUT),   # I2C SCL
                 Pin(num=5, name="SDO",   func=T.INPUT),   # I2C address LSB
                 Pin(num=6, name="VDDIO", func=T.PWRIN),
                 Pin(num=7, name="GND_7", func=T.PASSIVE),
                 Pin(num=8, name="VDD",   func=T.PWRIN)]
           )(value="SPA06-003",
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
v3v3_sys += u70["CSB"]            # CSB to VDDIO = I2C only (Table 11)
gnd      += u70["SDO"]            # SDO low  = address 0x76

# I2C1 + pull-ups (the bus's only pull-ups; shared with the expansion header)
scl = Net("I2C1_SCL"); scl += stm32["PB6"], u70["SCK"]
sda = Net("I2C1_SDA"); sda += stm32["PB7"], u70["SDA"]
r70 = Rn("R70", "5.1k"); scl += r70[1]; v3v3_sys += r70[2]   # Table 6: 5k-100k
r71 = Rn("R71", "5.1k"); sda += r71[1]; v3v3_sys += r71[2]

# ----------------------------------------------------------------------------
# Checks + output
# ----------------------------------------------------------------------------
ERC()
generate_netlist(tool=KICAD8, file_="baro.net")
print(">>> wrote baro.net")
