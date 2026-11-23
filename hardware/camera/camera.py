"""
DroneKit Pro - DVP camera block, as code.

Generates a KiCad-importable netlist for the 24-pin DVP camera (OV2640-class)
on the ESP32-S3: the FPC connector, the camera's own 2.8V and 1.2V rails, and
the control-line pulls.

    +3V3_ESP --> XC6206P282MR --> +2V8_CAM  (AVDD, analog)
    +3V3_ESP --> XC6206P122MR --> +1V2_CAM  (DVDD, sensor core)
    +3V3_ESP ------------------> DOVDD      (I/O, matches ESP32-S3 3.3V logic)

Design reference: hardware/camera/camera-design.md

Decisions encoded here:
  1. PWDN has a pull-UP to +3V3_ESP. The camera sits in power-down unless the
     ESP32-S3 drives GPIO14 low, so in Mode A (S3 held off by the dual-boot
     EN pull-down) the camera draws standby current only. Same dark-by-default
     idea as the ESP32 EN line.
  2. RESETB is an RC (10k to DOVDD, 100nF to GND): the camera comes out of
     reset on its own after power-up. No GPIO spent.
  3. SCCB (I2C-like) gets 4.7k pull-ups. The driver's internal pull-ups are
     too weak to rely on.
  4. Camera data pins follow Espressif's ESP32-S3-EYE map (checked against
     CAMERA_MODEL_ESP32S3_EYE in arduino-esp32 camera_pins.h). Y0/Y1 are the
     unused low bits of the 10-bit bus and stay unconnected.

FPC pin numbers follow the SunFounder ESP32 camera extension table (pin 1 = Y0,
pin 24 = NC). Some ESP32-CAM schematics number the same connector the other
way round (pin 1 = NC ... pin 24 = Y0). The signal ORDER is the same in both;
check the chosen FPC connector's pin-1 side against the module's ribbon before
layout (AGND/DGND pins ring through to the module's metal shield).

Refs are PINNED in a reserved 30+ range so this block never collides with the
dual-boot block (auto U1/U2, R1-R6, C1-C4, SW1/2) or the power block (10-20).
U2 here is the SAME ESP32-S3 as dual-boot U2; only its camera pins are listed.
Run:  python3 camera.py   ->  writes camera.net + prints ERC.
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

def Cn(ref, value, footprint=None):
    p = C(value=value)
    if footprint:
        p.footprint = footprint
    p.ref = ref
    return p

# ----------------------------------------------------------------------------
# Regulators: XC6206 family, SOT-23: 1 VSS  2 VOUT  3 VIN  (no EN, always-on)
# 2.8V: XC6206P282MR (e.g. LCSC C347374, 250mA)
# 1.2V: XC6206P122MR (e.g. LCSC C2827649, 200mA - NOT the 60mA Torex -G variant)
# Verify the SOT-23 pin order on the exact vendor's datasheet; clones vary.
# ----------------------------------------------------------------------------
def LDO(ref, value):
    p = Part(name=value, tool=SKIDL, ref_prefix="U", dest=TEMPLATE,
             pins=[Pin(num=1, name="VSS",  func=T.PWRIN),
                   Pin(num=2, name="VOUT", func=T.PWROUT),
                   Pin(num=3, name="VIN",  func=T.PWRIN)]
             )(value=value, footprint="Package_TO_SOT_SMD:SOT-23")
    p.ref = ref
    return p

u30 = LDO("U30", "XC6206P282MR")    # +2V8_CAM
u31 = LDO("U31", "XC6206P122MR")    # +1V2_CAM

# ----------------------------------------------------------------------------
# 24-pin 0.5mm FPC connector (flip-lock). Footprint is a stock KiCad one of the
# right pitch/pin count; swap for the exact LCSC part chosen at layout.
# ----------------------------------------------------------------------------
FPC_PINS = {
    1: "Y0",    2: "Y1",    3: "Y4",    4: "Y3",    5: "Y5",    6: "Y2",
    7: "Y6",    8: "PCLK",  9: "Y7",   10: "DGND", 11: "Y8",   12: "XCLK",
   13: "Y9",   14: "DOVDD",15: "DVDD", 16: "HREF", 17: "PWDN", 18: "VSYNC",
   19: "RESET",20: "SIOC", 21: "AVDD", 22: "SIOD", 23: "AGND", 24: "NC",
}
_fpc_func = {"DGND": T.PWRIN, "AGND": T.PWRIN, "DOVDD": T.PWRIN, "DVDD": T.PWRIN,
             "AVDD": T.PWRIN, "Y0": T.NOCONNECT, "Y1": T.NOCONNECT, "NC": T.NOCONNECT}
j30 = Part(name="FPC_24P_0.5mm", tool=SKIDL, ref_prefix="J", dest=TEMPLATE,
           pins=[Pin(num=n, name=s, func=_fpc_func.get(s, T.PASSIVE))
                 for n, s in FPC_PINS.items()]
           )(value="CAM_FPC_24P",
             footprint="Connector_FFC-FPC:Hirose_FH12-24S-0.5SH_1x24-1MP_P0.50mm_Horizontal")
j30.ref = "J30"

# ----------------------------------------------------------------------------
# ESP32-S3-WROOM-1-N8R2 (same part as dual-boot U2) - camera pins only.
# Pin numbers here are local to this script, not module pad numbers.
# ----------------------------------------------------------------------------
S3_CAM = [  # (GPIO, signal, pin type)
    (15, "XCLK",  T.OUTPUT), (4,  "SIOD", T.BIDIR),  (5,  "SIOC",  T.OUTPUT),
    (6,  "VSYNC", T.INPUT),  (7,  "HREF", T.INPUT),  (13, "PCLK",  T.INPUT),
    (11, "Y2",    T.INPUT),  (9,  "Y3",   T.INPUT),  (8,  "Y4",    T.INPUT),
    (10, "Y5",    T.INPUT),  (12, "Y6",   T.INPUT),  (18, "Y7",    T.INPUT),
    (17, "Y8",    T.INPUT),  (16, "Y9",   T.INPUT),  (14, "PWDN",  T.OUTPUT),
]
s3 = Part(name="ESP32-S3-WROOM-1-N8R2", tool=SKIDL, ref_prefix="U", dest=TEMPLATE,
          pins=[Pin(num=1, name="3V3", func=T.PWRIN), Pin(num=2, name="GND", func=T.PWRIN)] +
               [Pin(num=3 + i, name=f"IO{g}", func=f) for i, (g, _, f) in enumerate(S3_CAM)]
          )(value="ESP32-S3-WROOM-1-N8R2", footprint="RF_Module:ESP32-S3-WROOM-1")
s3.ref = "U2"

# ----------------------------------------------------------------------------
# Nets
# ----------------------------------------------------------------------------
v3v3_esp = Net("+3V3_ESP"); v3v3_esp.drive = Pin.drives.POWER   # from power block
gnd      = Net("GND");      gnd.drive      = Pin.drives.POWER
v2v8     = Net("+2V8_CAM")   # driven by U30
v1v2     = Net("+1V2_CAM")   # driven by U31

v3v3_esp += s3["3V3"]
gnd      += s3["GND"]

# ----------------------------------------------------------------------------
# Camera rails
# ----------------------------------------------------------------------------
v3v3_esp += u30["VIN"], u31["VIN"]
gnd      += u30["VSS"], u31["VSS"]
v2v8     += u30["VOUT"]
v1v2     += u31["VOUT"]

c30 = Cn("C30", "1uF");  v3v3_esp += c30[1]; gnd += c30[2]   # U30 in
c31 = Cn("C31", "1uF");  v2v8     += c31[1]; gnd += c31[2]   # U30 out
c32 = Cn("C32", "1uF");  v3v3_esp += c32[1]; gnd += c32[2]   # U31 in
c33 = Cn("C33", "1uF");  v1v2     += c33[1]; gnd += c33[2]   # U31 out

# Connector supplies + 100nF at each supply pin, placed at J30
v3v3_esp += j30["DOVDD"]
v1v2     += j30["DVDD"]
v2v8     += j30["AVDD"]
gnd      += j30["DGND"], j30["AGND"]
c34 = Cn("C34", "100nF"); v3v3_esp += c34[1]; gnd += c34[2]   # DOVDD
c35 = Cn("C35", "100nF"); v1v2     += c35[1]; gnd += c35[2]   # DVDD
c36 = Cn("C36", "100nF"); v2v8     += c36[1]; gnd += c36[2]   # AVDD

# ----------------------------------------------------------------------------
# Camera signals: connector <-> ESP32-S3
# ----------------------------------------------------------------------------
cam = {}
for g, sig, _ in S3_CAM:
    cam[sig] = Net(f"CAM_{sig}")
    cam[sig] += s3[f"IO{g}"], j30[sig]

# PWDN pull-UP: camera powered down unless the S3 drives it low (Mode B)
r30 = Rn("R30", "10k"); cam["PWDN"] += r30[1]; v3v3_esp += r30[2]

# SCCB pull-ups
r31 = Rn("R31", "4.7k"); cam["SIOD"] += r31[1]; v3v3_esp += r31[2]
r32 = Rn("R32", "4.7k"); cam["SIOC"] += r32[1]; v3v3_esp += r32[2]

# RESETB: RC power-on reset (active low)
cam_reset = Net("CAM_RESET")
r33 = Rn("R33", "10k");   cam_reset += j30["RESET"], r33[1]; v3v3_esp += r33[2]
c37 = Cn("C37", "100nF"); cam_reset += c37[1];               gnd      += c37[2]

# ----------------------------------------------------------------------------
# Checks + output
# ----------------------------------------------------------------------------
ERC()
generate_netlist(tool=KICAD8, file_="camera.net")
print(">>> wrote camera.net")
