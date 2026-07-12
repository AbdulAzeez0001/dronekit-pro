"""
DroneKit Pro - power tree, as code.

Generates a KiCad-importable netlist for Block 1: the supply chain that feeds
the whole board from a 2S LiPo.

    2S LiPo (VBAT) --[reverse-polarity P-FET]--> MP2307 buck --> +5V
        +5V --> RT9013-33  --> +3V3_SYS   (STM32 + sensors)
        +5V --> AP7361C-33 --> +3V3_ESP   (ESP32 only)

Design reference: hardware/power/power-design.md

The split rails are deliberate: +3V3_SYS (RT9013) and +3V3_ESP (AP7361C, 1A)
stay separate so ESP32 TX current bursts never sag the STM32/sensor rail.

Three details a generic generator gets wrong here, all datasheet-driven:
  1. Reverse-polarity protection is a high-side P-FET (DMG3415U-7) with the
     body diode oriented to block reverse current: Drain->battery, Source->load,
     Gate->GND via 100k. Logic-only rail (<1A); motors live on the ESC.
  2. The MP2307 needs more than caps: soft-start (SS), COMP compensation, EN
     auto-start pull-up, and - because 2S->5V runs ~68% duty, above the 65%
     line - an EXTERNAL bootstrap diode (1N4148, Vout->BS) with a 0.1uF BS cap.
     FB divider 44.2k/10k -> 5.01V; COMP 12k+3.9nF from MPS datasheet.
  3. AP7361C-33E is SOT-223 (3-pin, no EN) - always-on; the ESP is gated by
     its own EN pin in the dual-boot block, not by this rail.

Refs are PINNED in a reserved 10+ range (not auto-numbered like dual_boot.py)
so this block never collides with the dual-boot subcircuit (U1/U2, R1-R8,
C1-C4, SW1/2) when both import into one board.
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
# Pinouts verified against MPS (MP2307), Richtek (RT9013), Diodes (AP7361C,
# DMG3415U) datasheets.
# ----------------------------------------------------------------------------
# MP2307DN buck  SOIC-8-EP: 1 BS 2 IN 3 SW 4 GND 5 FB 6 COMP 7 EN 8 SS 9 EP(GND)
u10 = Part(name="MP2307DN", tool=SKIDL, ref_prefix="U", dest=TEMPLATE,
           pins=[Pin(num=1, name="BS",   func=T.PASSIVE),
                 Pin(num=2, name="IN",   func=T.PWRIN),
                 Pin(num=3, name="SW",   func=T.OUTPUT),
                 Pin(num=4, name="GND",  func=T.PWRIN),
                 Pin(num=5, name="FB",   func=T.PASSIVE),
                 Pin(num=6, name="COMP", func=T.PASSIVE),
                 Pin(num=7, name="EN",   func=T.PASSIVE),
                 Pin(num=8, name="SS",   func=T.PASSIVE),
                 Pin(num=9, name="EP",   func=T.PWRIN)]
           )(value="MP2307DN",
             footprint="Package_SO:SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.29x3mm")
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

# DMG3415U-7 P-FET  SOT-23: 1 G 2 S 3 D
q10 = Part(name="DMG3415U-7", tool=SKIDL, ref_prefix="Q", dest=TEMPLATE,
           pins=[Pin(num=1, name="G", func=T.PASSIVE),
                 Pin(num=2, name="S", func=T.PASSIVE),
                 Pin(num=3, name="D", func=T.PASSIVE)]
           )(value="DMG3415U-7", footprint="Package_TO_SOT_SMD:SOT-23")
q10.ref = "Q10"

# 1N4148 external bootstrap diode  SOD-323: 1 K 2 A
d10 = Part(name="1N4148", tool=SKIDL, ref_prefix="D", dest=TEMPLATE,
           pins=[Pin(num=1, name="K", func=T.PASSIVE),
                 Pin(num=2, name="A", func=T.PASSIVE)]
           )(value="1N4148", footprint="Diode_SMD:D_SOD-323")
d10.ref = "D10"

# FNR6045S100MT 10uH shielded inductor (LCSC C168076)
# footprint: closest stock 6.0x6.0 2-pad; verify land vs FNR6045 datasheet in KiCad
l10 = Part(name="FNR6045S100MT", tool=SKIDL, ref_prefix="L", dest=TEMPLATE,
           pins=[Pin(num=1, name="1", func=T.PASSIVE),
                 Pin(num=2, name="2", func=T.PASSIVE)]
           )(value="10uH", footprint="Inductor_SMD:L_Taiyo-Yuden_NR-60xx")
l10.ref = "L10"

# 2S LiPo battery input (placeholder footprint - swap for real connector, e.g. XT30)
j10 = Part(name="Conn_2S_LiPo", tool=SKIDL, ref_prefix="J", dest=TEMPLATE,
           pins=[Pin(num=1, name="VBAT", func=T.PWROUT),
                 Pin(num=2, name="GND",  func=T.PWRIN)]
           )(value="2S_LiPo",
             footprint="Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical")
j10.ref = "J10"

# ----------------------------------------------------------------------------
# Nets
# ----------------------------------------------------------------------------
vbat_raw = Net("VBAT_RAW"); vbat_raw.drive = Pin.drives.POWER  # battery+ pre-FET
vbat     = Net("VBAT");     vbat.drive     = Pin.drives.POWER  # protected -> buck
v5       = Net("+5V");      v5.drive       = Pin.drives.POWER
v3v3_sys = Net("+3V3_SYS")   # driven by RT9013 VOUT
v3v3_esp = Net("+3V3_ESP")   # driven by AP7361C OUT
gnd      = Net("GND");      gnd.drive      = Pin.drives.POWER

sw       = Net("SW")
bst      = Net("BST")
fb       = Net("FB")
comp     = Net("COMP")
comp_mid = Net("COMP_MID")
q_gate   = Net("Q10_GATE")
mp_en    = Net("MP_EN")
mp_ss    = Net("MP_SS")

# ----------------------------------------------------------------------------
# Battery input + reverse-polarity protection (high-side P-FET)
# ----------------------------------------------------------------------------
vbat_raw += j10[1], q10["D"]
gnd      += j10[2]
vbat     += q10["S"]
r10 = Rn("R10", "100k")                     # gate pulldown: FET off until battery present
q_gate += q10["G"], r10[1]; gnd += r10[2]

# ----------------------------------------------------------------------------
# MP2307 buck: VBAT -> +5V
# ----------------------------------------------------------------------------
vbat += u10["IN"]
gnd  += u10["GND"], u10["EP"]
sw   += u10["SW"]
bst  += u10["BS"]
fb   += u10["FB"]
comp += u10["COMP"]

c10 = Cn("C10", "10uF", "Capacitor_SMD:C_1206_3216Metric")   # Cin 2x10uF/25V
c11 = Cn("C11", "10uF", "Capacitor_SMD:C_1206_3216Metric")
vbat += c10[1], c11[1]; gnd += c10[2], c11[2]

r14 = Rn("R14", "100k")                     # EN pull-up to IN -> auto-start
mp_en += u10["EN"], r14[1]; vbat += r14[2]

c14 = Cn("C14", "0.1uF")                    # soft-start -> 15ms
mp_ss += u10["SS"], c14[1]; gnd += c14[2]

c15 = Cn("C15", "0.1uF")                    # bootstrap cap SW-BS
bst += c15[1]; sw += c15[2]
v5  += d10["A"]; bst += d10["K"]            # ext BS diode +5V->BS (duty >65%)

l10[1] += sw; l10[2] += v5                   # 10uH output inductor
c12 = Cn("C12", "22uF", "Capacitor_SMD:C_0805_2012Metric")   # Cout 2x22uF
c13 = Cn("C13", "22uF", "Capacitor_SMD:C_0805_2012Metric")
v5 += c12[1], c13[1]; gnd += c12[2], c13[2]

r11 = Rn("R11", "44.2k")                    # FB divider top  -> 5.01V
r12 = Rn("R12", "10k")                      # FB divider bottom
v5 += r11[1]; fb += r11[2], r12[1]; gnd += r12[2]

r13 = Rn("R13", "12k")                      # COMP network 12k + 3.9nF (MPS datasheet)
c16 = Cn("C16", "3.9nF")
comp += r13[1]; comp_mid += r13[2], c16[1]; gnd += c16[2]

# ----------------------------------------------------------------------------
# RT9013-33 LDO: +5V -> +3V3_SYS  (STM32 + sensors)
# ----------------------------------------------------------------------------
v5       += u11["VIN"], u11["EN"]            # EN tied to VIN = always-on
gnd      += u11["GND"]
v3v3_sys += u11["VOUT"]
c17 = Cn("C17", "1uF");  v5 += c17[1]; gnd += c17[2]
c18 = Cn("C18", "10uF", "Capacitor_SMD:C_0805_2012Metric")
v3v3_sys += c18[1]; gnd += c18[2]

# ----------------------------------------------------------------------------
# AP7361C-33 LDO: +5V -> +3V3_ESP  (ESP32 only)
# ----------------------------------------------------------------------------
v5       += u12["IN"]
gnd      += u12["GND"]
v3v3_esp += u12["OUT"]
c19 = Cn("C19", "1uF");  v5 += c19[1]; gnd += c19[2]
c20 = Cn("C20", "10uF", "Capacitor_SMD:C_0805_2012Metric")   # LDO bulk
v3v3_esp += c20[1]; gnd += c20[2]

# ----------------------------------------------------------------------------
# Checks + output
# ----------------------------------------------------------------------------
ERC()
generate_netlist(tool=KICAD8, file_="power.net")
print(">>> wrote power.net")
