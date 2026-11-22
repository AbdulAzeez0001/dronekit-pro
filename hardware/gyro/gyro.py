"""
DroneKit Pro - ICM-42688-P gyro/accelerometer block, as code.

Generates a KiCad-importable netlist for the ICM-42688-P IMU on the STM32's
SPI1, with its data-ready interrupt on PC4. This is the sensor Betaflight
stabilises the quad with, so it gets SPI1 to itself and the clean rail.
(Replaces the MPU-6000, which is end-of-life; same STM32 pins.)

    +3V3_SYS --> U80 ICM-42688-P VDD (0.1uF + 2.2uF) and VDDIO (10nF)
    STM32 PA5 (SPI1_SCK)  --> AP_SCLK (pin 13)
    STM32 PA6 (SPI1_MISO) <-- AP_SDO  (pin 1)
    STM32 PA7 (SPI1_MOSI) --> AP_SDI  (pin 14)
    STM32 PA4 (CS)        --> AP_CS   (pin 12, 10k pull-up)
    STM32 PC4 (EXTI4)     <-- INT1    (pin 4)
    INT2/FSYNC/CLKIN (pin 9) and all RESV pins -> GND

Design reference: hardware/gyro/gyro-design.md

Values and pins from the TDK InvenSense ICM-42688-P datasheet (DS-000347,
rev 1.2), section 4.1 (Table 9, signal descriptions) and section 4.3
(Table 10, external components):
  C1 VDD bypass   0.1uF X7R      C2 VDD bypass  2.2uF X7R
  C3 VDDIO bypass 10nF  X7R
  Pin 7 RESV: connect to GND.  Pins 2, 3, 10, 11 RESV: no connect or GND.
  Pin 9 INT2/FSYNC/CLKIN: connect to GND if FSYNC not used.
  SPI up to 24 MHz.

Decisions encoded here:
  1. SPI, 4-wire: fast reads for Betaflight's 8 kHz gyro loop.
  2. AP_CS pull-up (10k): AP_CS low selects the SPI interface, and the STM32
     pin floats until firmware starts, so the pull-up keeps it deselected.
  3. All RESV pins to GND (the datasheet allows it for 2/3/10/11 and
     requires it for 7): solid ground under the sensor, nothing floating.
  4. Pin 9 to GND: no FSYNC, and no external clock (Betaflight runs the
     ICM-42688-P from its internal oscillator).
  5. VDD and VDDIO both on +3V3_SYS, the clean RT9013 rail: gyro supply
     noise turns straight into flight noise.

U1 here is the SAME STM32F405 as dual-boot U1; only these pins are listed.
Refs are PINNED in a reserved 80-89 range so this block never collides with
dual-boot (auto), power (10-29), camera (30-39), motors (40-59), receiver
port (60-69) or baro (70-79).
Run:  python3 gyro.py   ->  writes gyro.net + prints ERC.
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
# ICM-42688-P, LGA-14 2.5 x 3.0 x 0.91 mm (datasheet pin numbers)
# Footprint: KiCad LGA-14 3x2.5mm P0.5mm (3 + 4 pads per side) - verify
# against the datasheet land pattern before layout.
# ----------------------------------------------------------------------------
u80 = Part(name="ICM-42688-P", tool=SKIDL, ref_prefix="U", dest=TEMPLATE,
           pins=[Pin(num=1,  name="AP_SDO",  func=T.OUTPUT),   # SPI MISO
                 Pin(num=2,  name="RESV_2",  func=T.PASSIVE),
                 Pin(num=3,  name="RESV_3",  func=T.PASSIVE),
                 Pin(num=4,  name="INT1",    func=T.OUTPUT),
                 Pin(num=5,  name="VDDIO",   func=T.PWRIN),
                 Pin(num=6,  name="GND",     func=T.PWRIN),
                 Pin(num=7,  name="RESV_7",  func=T.PASSIVE),  # must go to GND
                 Pin(num=8,  name="VDD",     func=T.PWRIN),
                 Pin(num=9,  name="INT2",    func=T.PASSIVE),  # INT2/FSYNC/CLKIN
                 Pin(num=10, name="RESV_10", func=T.PASSIVE),
                 Pin(num=11, name="RESV_11", func=T.PASSIVE),
                 Pin(num=12, name="AP_CS",   func=T.INPUT),
                 Pin(num=13, name="AP_SCLK", func=T.INPUT),
                 Pin(num=14, name="AP_SDI",  func=T.INPUT)]    # SPI MOSI
           )(value="ICM-42688-P",
             footprint="Package_LGA:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y")
u80.ref = "U80"

# STM32F405 (same part as dual-boot U1) - SPI1 + gyro INT. Local pin numbers.
stm32 = Part(name="STM32F405RGT6", tool=SKIDL, ref_prefix="U", dest=TEMPLATE,
             pins=[Pin(num=1, name="VSS", func=T.PWRIN),
                   Pin(num=2, name="PA5", func=T.OUTPUT),   # SPI1_SCK
                   Pin(num=3, name="PA6", func=T.INPUT),    # SPI1_MISO
                   Pin(num=4, name="PA7", func=T.OUTPUT),   # SPI1_MOSI
                   Pin(num=5, name="PA4", func=T.OUTPUT),   # gyro CS
                   Pin(num=6, name="PC4", func=T.INPUT)]    # gyro INT (EXTI4)
             )(value="STM32F405RGT6", footprint="Package_QFP:LQFP-64_10x10mm_P0.5mm")
stm32.ref = "U1"

# ----------------------------------------------------------------------------
# Nets
# ----------------------------------------------------------------------------
v3v3_sys = Net("+3V3_SYS"); v3v3_sys.drive = Pin.drives.POWER   # from power block (RT9013)
gnd      = Net("GND");      gnd.drive      = Pin.drives.POWER
gnd += stm32["VSS"]

# Supply + datasheet external components (Table 10)
v3v3_sys += u80["VDD"], u80["VDDIO"]
c80 = Cn("C80", "100nF")                                  # C1: VDD bypass
c81 = Cn("C81", "2.2uF"); c81.footprint = "Capacitor_SMD:C_0603_1608Metric"  # C2: VDD bypass
c82 = Cn("C82", "10nF")                                   # C3: VDDIO bypass
v3v3_sys += c80[1], c81[1], c82[1]
gnd      += c80[2], c81[2], c82[2]

# Ground, reserved pins and unused INT2/FSYNC/CLKIN
gnd += u80["GND"], u80["RESV_7"]                         # pin 7 must be grounded
gnd += u80["RESV_2"], u80["RESV_3"], u80["RESV_10"], u80["RESV_11"]
gnd += u80["INT2"]                                       # FSYNC unused, no ext clock

# SPI1 + interrupt
def link(name, *pins):
    n = Net(name); n += pins; return n

link("GYRO_SCK",  stm32["PA5"], u80["AP_SCLK"])
link("GYRO_MISO", stm32["PA6"], u80["AP_SDO"])
link("GYRO_MOSI", stm32["PA7"], u80["AP_SDI"])
cs = link("GYRO_CS", stm32["PA4"], u80["AP_CS"])
link("GYRO_INT",  stm32["PC4"], u80["INT1"])

r80 = Rn("R80", "10k")             # AP_CS pull-up: IMU deselected while the STM32 boots
cs += r80[1]; v3v3_sys += r80[2]

# ----------------------------------------------------------------------------
# Checks + output
# ----------------------------------------------------------------------------
ERC()
generate_netlist(tool=KICAD8, file_="gyro.net")
print(">>> wrote gyro.net")
