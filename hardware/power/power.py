"""
DroneKit Pro - power tree, as code.

Generates a KiCad-importable netlist for Block 1: the supply chain that feeds
the whole board from a 1S OR 2S LiPo, with no jumper or setting to change.

    1S/2S LiPo (VBAT_RAW, 3.0-8.4V)
        --[reverse-polarity P-FET]--> VBAT
        VBAT --> TPS63070 buck-boost --> +3V8 (pre-regulator)
            +3V8 --> RT9013-33  --> +3V3_SYS   (STM32 + sensors, clean)
            +3V8 --> AP7361C-33 --> +3V3_ESP   (ESP32-S3 + camera)
        VBAT --> 10k/1k divider --> VBAT_SENSE (STM32 PC1, cell-count detect)

Design reference: hardware/power/power-design.md

Why this shape:
  1. One converter covers both packs. A 1S cell sags to ~3.0V under motor
     load (below 3.3V); a 2S pack sits at 6.0-8.4V. A plain buck can't do 1S
     and a plain boost can't do 2S. The TPS63070 buck-boost runs from 2.0V to
     16V in (UVLO falling 1.85V typ) and switches between buck and boost by
     itself.
  2. It makes 3.8V, not 3.3V, so the two existing LDOs still have headroom.
     They keep the split-rail design (gyro rail isolated from ESP32 WiFi
     bursts) and they filter the converter's 2.4MHz ripple off the gyro rail.
  3. Reverse-polarity P-FET is now AO3401A (Vgs +/-12V). The old DMG3415U is
     only rated Vgs +/-8V, and a full 2S pack puts 8.4V on the gate.
  4. PS/SYNC is tied LOW = forced fixed-frequency PWM. Steady 2.4MHz ripple is
     far easier for the LDOs to reject than power-save-mode bursts.

TPS63070 values from TI SLVSC58B (Rev. B, 2019), section 9.2:
  VFB = 0.8V, Vout = 0.8 * (1 + R11/R12). R11 374k / R12 100k -> 3.79V.
  L = 1.5uH (XFL4020-152ME), Cin 2x10uF 0805 + 10uF 0603 at the pins,
  Cout 2x22uF 0805 + 10uF 0603 at the pins (Vout <= 5V -> 2x22uF),
  VAUX 100nF (must not be loaded), EN to VIN through a series resistor,
  PG open-drain with 100k pull-up, VSEL low + FB2 open (single output voltage).
  Buck-mode duty at 8.4V in = 3.8/8.4 = 45%, above the 30% minimum.

Refs are PINNED in a reserved 10-29 range (not auto-numbered like dual_boot.py)
so this block never collides with the dual-boot subcircuit (U1/U2, R1-R6,
C1-C4, SW1/2) or the camera block (30+) when they import into one board.
Run:  python3 power.py   ->  writes power.net + prints ERC.
"""

from skidl import Part, Pin, Net, SKIDL, KICAD8, TEMPLATE, generate_netlist, ERC, set_default_tool

set_default_tool(SKIDL)
T = Pin.types

# ----------------------------------------------------------------------------
# Passive templates + ref-pinning helpers (second block -> explicit refs)
# ----------------------------------------------------------------------------
R = Part(name="R", tool=SKIDL, ref_prefix="R", dest=TEMPLATE,
         footprint="Resistor_SMD:R_0402_1005Metric",
         pins=[Pin(num=1, name="1", func=T.PASSIVE),
               Pin(num=2, name="2", func=T.PASSIVE)])

C = Part(name="C", tool=SKIDL, ref_prefix="C", dest=TEMPLATE,
         footprint="Capacitor_SMD:C_0402_1005Metric",
         pins=[Pin(num=1, name="1", func=T.PASSIVE),
               Pin(num=2, name="2", func=T.PASSIVE)])

C0603 = "Capacitor_SMD:C_0603_1608Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"

def Rn(ref, value):
    p = R(value=value); p.ref = ref; return p

def Cn(ref, value, footprint=None):
    p = C(value=value)
    if footprint:
        p.footprint = footprint
    p.ref = ref
    return p

# ----------------------------------------------------------------------------
# Active / discrete parts - only the pins this block uses are defined.
# ----------------------------------------------------------------------------
# TPS63070RNM buck-boost, VQFN-HR 15 pin (TI pin table, SLVSC58B section 6):
#  1 PS/SYNC  2 PG  3 VAUX  4 GND  5 FB  6 FB2  7,8 VOUT  9 L2  10 PGND
#  11 L1  12,13 VIN  14 EN  15 VSEL
# Footprint: no stock KiCad footprint confirmed for RNM0015A - import TI's.
u10 = Part(name="TPS63070RNM", tool=SKIDL, ref_prefix="U", dest=TEMPLATE,
           pins=[Pin(num=1,  name="PS/SYNC", func=T.INPUT),
                 Pin(num=2,  name="PG",      func=T.OPENCOLL),
                 Pin(num=3,  name="VAUX",    func=T.PASSIVE),
                 Pin(num=4,  name="GND",     func=T.PWRIN),
                 Pin(num=5,  name="FB",      func=T.INPUT),
                 Pin(num=6,  name="FB2",     func=T.NOCONNECT),   # unused: VSEL low
                 Pin(num=7,  name="VOUT",    func=T.PWROUT),
                 Pin(num=8,  name="VOUT_2",  func=T.PASSIVE),   # same node as pin 7
                 Pin(num=9,  name="L2",      func=T.PASSIVE),
                 Pin(num=10, name="PGND",    func=T.PWRIN),
                 Pin(num=11, name="L1",      func=T.PASSIVE),
                 Pin(num=12, name="VIN",     func=T.PWRIN),
                 Pin(num=13, name="VIN_2",   func=T.PWRIN),
                 Pin(num=14, name="EN",      func=T.INPUT),
                 Pin(num=15, name="VSEL",    func=T.INPUT)]
           )(value="TPS63070RNM", footprint="TI:RNM0015A")
u10.ref = "U10"

# RT9013-33GB LDO  SOT-23-5: 1 VIN 2 GND 3 EN 4 NC 5 VOUT (EN tied to VIN)
u11 = Part(name="RT9013-33GB", tool=SKIDL, ref_prefix="U", dest=TEMPLATE,
           pins=[Pin(num=1, name="VIN",  func=T.PWRIN),
                 Pin(num=2, name="GND",  func=T.PWRIN),
                 Pin(num=3, name="EN",   func=T.PASSIVE),
                 Pin(num=4, name="NC",   func=T.NOCONNECT),
                 Pin(num=5, name="VOUT", func=T.PWROUT)]
           )(value="RT9013-33GB", footprint="Package_TO_SOT_SMD:SOT-23-5")
u11.ref = "U11"

# AP7361C-33E LDO  SOT-223 (no EN): 1 IN 2 GND(+tab) 3 OUT - always-on
u12 = Part(name="AP7361C-33E", tool=SKIDL, ref_prefix="U", dest=TEMPLATE,
           pins=[Pin(num=1, name="IN",  func=T.PWRIN),
                 Pin(num=2, name="GND", func=T.PWRIN),
                 Pin(num=3, name="OUT", func=T.PWROUT)]
           )(value="AP7361C-33E", footprint="Package_TO_SOT_SMD:SOT-223-3_TabPin2")
u12.ref = "U12"

# AO3401A P-FET  SOT-23: 1 G 2 S 3 D.  Vds -30V, Vgs +/-12V (2S-safe gate).
q10 = Part(name="AO3401A", tool=SKIDL, ref_prefix="Q", dest=TEMPLATE,
           pins=[Pin(num=1, name="G", func=T.PASSIVE),
                 Pin(num=2, name="S", func=T.PASSIVE),
                 Pin(num=3, name="D", func=T.PASSIVE)]
           )(value="AO3401A", footprint="Package_TO_SOT_SMD:SOT-23")
q10.ref = "Q10"

# 1.5uH inductor, TI-recommended Coilcraft XFL4020-152ME (4x4x2.1, Isat 4.6A).
# Any shielded 1.5uH with Isat >= ~2A and low DCR works (pick an LCSC part).
l10 = Part(name="XFL4020-152ME", tool=SKIDL, ref_prefix="L", dest=TEMPLATE,
           pins=[Pin(num=1, name="1", func=T.PASSIVE),
                 Pin(num=2, name="2", func=T.PASSIVE)]
           )(value="1.5uH", footprint="Inductor_SMD:L_Coilcraft_XFL4020-XXX")
l10.ref = "L10"

# Battery input: 1S or 2S. Solder pads for a pigtail (motor current flows here
# too on 1S whoops, so no small JST-PH). Placeholder footprint.
j10 = Part(name="Conn_VBAT_1S_2S", tool=SKIDL, ref_prefix="J", dest=TEMPLATE,
           pins=[Pin(num=1, name="VBAT", func=T.PWROUT),
                 Pin(num=2, name="GND",  func=T.PWRIN)]
           )(value="VBAT_1S_2S",
             footprint="Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical")
j10.ref = "J10"

# ----------------------------------------------------------------------------
# Nets
# ----------------------------------------------------------------------------
vbat_raw = Net("VBAT_RAW"); vbat_raw.drive = Pin.drives.POWER  # battery+ pre-FET (motors)
vbat     = Net("VBAT");     vbat.drive     = Pin.drives.POWER  # protected -> logic supply
v3v8     = Net("+3V8")       # driven by TPS63070 VOUT
v3v3_sys = Net("+3V3_SYS")   # driven by RT9013 VOUT
v3v3_esp = Net("+3V3_ESP")   # driven by AP7361C OUT
gnd      = Net("GND");      gnd.drive      = Pin.drives.POWER

sw1      = Net("BB_L1")
sw2      = Net("BB_L2")
fb       = Net("BB_FB")
vaux     = Net("BB_VAUX")
bb_en    = Net("BB_EN")
pg       = Net("PG_3V8")
q_gate   = Net("Q10_GATE")
vbat_sns = Net("VBAT_SENSE")

# ----------------------------------------------------------------------------
# Battery input + reverse-polarity protection (high-side P-FET)
# ----------------------------------------------------------------------------
vbat_raw += j10[1], q10["D"]
gnd      += j10[2]
vbat     += q10["S"]
r10 = Rn("R10", "100k")                     # gate pulldown: FET on only with correct polarity
q_gate += q10["G"], r10[1]; gnd += r10[2]

# ----------------------------------------------------------------------------
# TPS63070 buck-boost: VBAT (3.0-8.4V) -> +3V8
# ----------------------------------------------------------------------------
vbat += u10["VIN"], u10["VIN_2"]
gnd  += u10["GND"], u10["PGND"]
v3v8 += u10["VOUT"], u10["VOUT_2"]
sw1  += u10["L1"]
sw2  += u10["L2"]
l10[1] += sw1; l10[2] += sw2

c10 = Cn("C10", "10uF/25V", C0805)          # Cin: 2x10uF 0805 (2 needed above 6V in)
c11 = Cn("C11", "10uF/25V", C0805)
c12 = Cn("C12", "10uF/25V", C0603)          # 0603 right at the VIN pins
vbat += c10[1], c11[1], c12[1]; gnd += c10[2], c11[2], c12[2]

c13 = Cn("C13", "22uF/16V", C0805)          # Cout: 2x22uF 0805 (Vout <= 5V)
c14 = Cn("C14", "22uF/16V", C0805)
c15 = Cn("C15", "10uF/25V", C0603)          # 0603 right at the VOUT pins
v3v8 += c13[1], c14[1], c15[1]; gnd += c13[2], c14[2], c15[2]

c16 = Cn("C16", "100nF")                    # VAUX: internal regulator cap, no load
vaux += u10["VAUX"], c16[1]; gnd += c16[2]

r11 = Rn("R11", "374k")                     # FB top     } 0.8 * (1 + 374/100)
r12 = Rn("R12", "100k")                     # FB bottom  } = 3.79V
v3v8 += r11[1]; fb += u10["FB"], r11[2], r12[1]; gnd += r12[2]

r13 = Rn("R13", "100k")                     # EN to VIN via series R (TI: 1k-1M)
bb_en += u10["EN"], r13[1]; vbat += r13[2]

gnd += u10["PS/SYNC"]                       # LOW = forced PWM (steady 2.4MHz)
gnd += u10["VSEL"]                          # single output voltage; FB2 left open

r14 = Rn("R14", "100k")                     # PG open-drain pull-up
pg += u10["PG"], r14[1]; v3v8 += r14[2]

# ----------------------------------------------------------------------------
# RT9013-33 LDO: +3V8 -> +3V3_SYS  (STM32 + sensors, clean)
# ----------------------------------------------------------------------------
v3v8     += u11["VIN"], u11["EN"]           # EN tied to VIN = always-on
gnd      += u11["GND"]
v3v3_sys += u11["VOUT"]
c17 = Cn("C17", "1uF");  v3v8 += c17[1]; gnd += c17[2]
c18 = Cn("C18", "10uF", C0805)
v3v3_sys += c18[1]; gnd += c18[2]

# ----------------------------------------------------------------------------
# AP7361C-33 LDO: +3V8 -> +3V3_ESP  (ESP32-S3 + camera)
# ----------------------------------------------------------------------------
v3v8     += u12["IN"]
gnd      += u12["GND"]
v3v3_esp += u12["OUT"]
c19 = Cn("C19", "1uF");  v3v8 += c19[1]; gnd += c19[2]
c20 = Cn("C20", "10uF", C0805)              # LDO bulk
v3v3_esp += c20[1]; gnd += c20[2]

# ----------------------------------------------------------------------------
# Battery voltage sense -> STM32 PC1 (ADC). 10k/1k = Betaflight vbat_scale 110.
# 8.4V -> 0.76V, 4.2V -> 0.38V. Firmware reads this at boot to tell 1S from 2S.
# ----------------------------------------------------------------------------
r15 = Rn("R15", "10k")
r16 = Rn("R16", "1k")
c21 = Cn("C21", "100nF")                    # ADC filter
vbat += r15[1]; vbat_sns += r15[2], r16[1], c21[1]; gnd += r16[2], c21[2]

# ----------------------------------------------------------------------------
# Checks + output
# ----------------------------------------------------------------------------
ERC()
generate_netlist(tool=KICAD8, file_="power.net")
print(">>> wrote power.net")
