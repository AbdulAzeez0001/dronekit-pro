"""
DroneKit Pro - STM32F405 flight-controller block, as code.

Generates a KiCad-importable netlist for the STM32F405RGT6 itself: its
supplies and decoupling, the 8 MHz crystal, USB (to the Betaflight
configurator), the BOOT button for DFU flashing, SWD debug pads and the
status LED. It is also the MASTER pin map: U1 is defined here with all 64
real LQFP64 pin numbers, and every pin another block uses is tied to that
block's net name, so the blocks merge into one board by net name.

Design reference: hardware/stm32/stm32-design.md
Pin map:          hardware/stm32f405-pinmap.md

Values from ST DS8626 (STM32F405xx/F407xx datasheet), section 5.1.6
(power supply scheme) and the HSE oscillator section:
  - each VDD pin decoupled with 100nF at the pin; one 4.7uF on a VDD pin
  - VDDA = VDD, VSSA = VSS (100nF + 1uF at VDDA)
  - VCAP_1 / VCAP_2: 2.2uF ceramic each, ESR < 2 ohm (regulator ON;
    the LQFP64 has no BYPASS_REG/PDR_ON pins)
  - VBAT tied to VDD (no backup battery), 100nF
  - HSE load caps: CL = CL1*CL2/(CL1+CL2) + ~10pF stray. For a CL = 20pF
    crystal, CL1 = CL2 = 20pF.

Decisions encoded here:
  1. 8 MHz HSE crystal: what Betaflight's STM32F405 targets expect.
  2. USB-C, USB 2.0 full-speed (PA11/PA12). VBUS goes to the power block's
     USB power path (Schottky + battery-FET gate drive), which powers the
     logic without back-feeding the LiPo; motors never run from USB.
     CC1/CC2 5.1k pull-downs so USB-C hosts see a device; USBLC6-2SC6 ESD
     protection on D+/D-.
  3. BOOT button to 3.3V through 1k: holds BOOT0 high for DFU. The 1k
     protects the ESP32-S3 GPIO41 that also drives BOOT0 (STM_BOOT0 net,
     10k pull-down in the dual-boot block).
  4. PB2/BOOT1 pulled down (10k): system-memory boot needs BOOT1 = 0.
  5. SWD pads (3V3, SWDIO, SWCLK, NRST, GND) for debugging/recovery.
  6. Status LED on PB9 (Betaflight LED0), active low.

Refs are PINNED in a reserved 90-119 range so this block never collides with
dual-boot (auto), power (10-29), camera (30-39), motors (40-59), receiver
port (60-69), baro (70-79) or gyro (80-89).
Run:  python3 stm32.py   ->  writes stm32.net + prints ERC.
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

C0603 = "Capacitor_SMD:C_0603_1608Metric"

def Rn(ref, value):
    p = R(value=value); p.ref = ref; return p

def Cn(ref, value, footprint=None):
    p = C(value=value)
    if footprint:
        p.footprint = footprint
    p.ref = ref
    return p

# ----------------------------------------------------------------------------
# STM32F405RGT6, LQFP64 - all 64 pins, numbers per DS8626 Figure 12.
# ----------------------------------------------------------------------------
LQFP64 = {
     1: "VBAT",  2: "PC13",  3: "PC14",  4: "PC15",  5: "PH0",   6: "PH1",
     7: "NRST",  8: "PC0",   9: "PC1",  10: "PC2",  11: "PC3",  12: "VSSA",
    13: "VDDA", 14: "PA0",  15: "PA1",  16: "PA2",  17: "PA3",  18: "VSS_18",
    19: "VDD_19", 20: "PA4", 21: "PA5", 22: "PA6",  23: "PA7",  24: "PC4",
    25: "PC5",  26: "PB0",  27: "PB1",  28: "PB2",  29: "PB10", 30: "PB11",
    31: "VCAP_1", 32: "VDD_32", 33: "PB12", 34: "PB13", 35: "PB14", 36: "PB15",
    37: "PC6",  38: "PC7",  39: "PC8",  40: "PC9",  41: "PA8",  42: "PA9",
    43: "PA10", 44: "PA11", 45: "PA12", 46: "PA13", 47: "VCAP_2", 48: "VDD_48",
    49: "PA14", 50: "PA15", 51: "PC10", 52: "PC11", 53: "PC12", 54: "PD2",
    55: "PB3",  56: "PB4",  57: "PB5",  58: "PB6",  59: "PB7",  60: "BOOT0",
    61: "PB8",  62: "PB9",  63: "VSS_63", 64: "VDD_64",
}
POWER_PINS = {"VBAT", "VSSA", "VDDA", "VSS_18", "VDD_19", "VDD_32", "VDD_48",
              "VSS_63", "VDD_64"}

def _func(name):
    if name in POWER_PINS:
        return T.PWRIN
    if name in ("VCAP_1", "VCAP_2"):
        return T.PASSIVE
    return T.BIDIR

u1 = Part(name="STM32F405RGT6", tool=SKIDL, ref_prefix="U", dest=TEMPLATE,
          pins=[Pin(num=n, name=s, func=_func(s)) for n, s in LQFP64.items()]
          )(value="STM32F405RGT6", footprint="Package_QFP:LQFP-64_10x10mm_P0.5mm")
u1.ref = "U1"

# ----------------------------------------------------------------------------
# Other parts
# ----------------------------------------------------------------------------
# 8 MHz crystal, 3225 4-pad (1, 3 = crystal; 2, 4 = case GND)
y90 = Part(name="Crystal_GND24", tool=SKIDL, ref_prefix="Y", dest=TEMPLATE,
           pins=[Pin(num=1, name="1",   func=T.PASSIVE),
                 Pin(num=2, name="GND", func=T.PASSIVE),
                 Pin(num=3, name="3",   func=T.PASSIVE),
                 Pin(num=4, name="GND_4", func=T.PASSIVE)]
           )(value="8MHz CL=20pF", footprint="Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm")
y90.ref = "Y90"

# USB-C 2.0 receptacle (16-pin). Same-named pins are bonded on the part.
j90 = Part(name="USB_C_Receptacle_USB2.0", tool=SKIDL, ref_prefix="J", dest=TEMPLATE,
           pins=[Pin(num="A1",  name="GND_A1",   func=T.PASSIVE),
                 Pin(num="A4",  name="VBUS_A4",  func=T.PWROUT),
                 Pin(num="A5",  name="CC1",      func=T.PASSIVE),
                 Pin(num="A6",  name="DP_A6",    func=T.PASSIVE),
                 Pin(num="A7",  name="DN_A7",    func=T.PASSIVE),
                 Pin(num="A8",  name="SBU1",     func=T.NOCONNECT),
                 Pin(num="A9",  name="VBUS_A9",  func=T.PASSIVE),
                 Pin(num="A12", name="GND_A12",  func=T.PASSIVE),
                 Pin(num="B1",  name="GND_B1",   func=T.PASSIVE),
                 Pin(num="B4",  name="VBUS_B4",  func=T.PASSIVE),
                 Pin(num="B5",  name="CC2",      func=T.PASSIVE),
                 Pin(num="B6",  name="DP_B6",    func=T.PASSIVE),
                 Pin(num="B7",  name="DN_B7",    func=T.PASSIVE),
                 Pin(num="B8",  name="SBU2",     func=T.NOCONNECT),
                 Pin(num="B9",  name="VBUS_B9",  func=T.PASSIVE),
                 Pin(num="B12", name="GND_B12",  func=T.PASSIVE),
                 Pin(num="S1",  name="SHIELD",   func=T.PASSIVE)]
           )(value="USB-C", footprint="Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12")
j90.ref = "J90"

# USBLC6-2SC6 ESD, SOT-23-6: 1 I/O1  2 GND  3 I/O2  4 I/O2  5 VBUS  6 I/O1
u91 = Part(name="USBLC6-2SC6", tool=SKIDL, ref_prefix="U", dest=TEMPLATE,
           pins=[Pin(num=1, name="IO1",   func=T.PASSIVE),
                 Pin(num=2, name="GND",   func=T.PWRIN),
                 Pin(num=3, name="IO2",   func=T.PASSIVE),
                 Pin(num=4, name="IO2_4", func=T.PASSIVE),
                 Pin(num=5, name="VBUS",  func=T.PWRIN),
                 Pin(num=6, name="IO1_6", func=T.PASSIVE)]
           )(value="USBLC6-2SC6", footprint="Package_TO_SOT_SMD:SOT-23-6")
u91.ref = "U91"

sw90 = Part(name="SW_PUSH", tool=SKIDL, ref_prefix="SW", dest=TEMPLATE,
            pins=[Pin(num=1, name="A", func=T.PASSIVE),
                  Pin(num=2, name="B", func=T.PASSIVE)]
            )(value="BOOT", footprint="Button_Switch_SMD:SW_SPST_SKQG_WithStem")
sw90.ref = "SW90"

d90 = Part(name="LED", tool=SKIDL, ref_prefix="D", dest=TEMPLATE,
           pins=[Pin(num=1, name="K", func=T.PASSIVE),
                 Pin(num=2, name="A", func=T.PASSIVE)]
           )(value="LED_blue", footprint="LED_SMD:LED_0402_1005Metric")
d90.ref = "D90"

# SWD pads: 1 3V3  2 SWDIO  3 SWCLK  4 NRST  5 GND
j91 = Part(name="SWD_Pads", tool=SKIDL, ref_prefix="J", dest=TEMPLATE,
           pins=[Pin(num=1, name="3V3",   func=T.PASSIVE),
                 Pin(num=2, name="SWDIO", func=T.PASSIVE),
                 Pin(num=3, name="SWCLK", func=T.PASSIVE),
                 Pin(num=4, name="NRST",  func=T.PASSIVE),
                 Pin(num=5, name="GND",   func=T.PASSIVE)]
           )(value="SWD", footprint="Connector_PinHeader_1.27mm:PinHeader_1x05_P1.27mm_Vertical")
j91.ref = "J91"

# ----------------------------------------------------------------------------
# Power nets
# ----------------------------------------------------------------------------
v3v3_sys = Net("+3V3_SYS"); v3v3_sys.drive = Pin.drives.POWER   # from power block (RT9013)
gnd      = Net("GND");      gnd.drive      = Pin.drives.POWER

v3v3_sys += u1["VDD_19"], u1["VDD_32"], u1["VDD_48"], u1["VDD_64"], u1["VDDA"], u1["VBAT"]
gnd      += u1["VSS_18"], u1["VSS_63"], u1["VSSA"]

# 100nF at each VDD pin + 4.7uF on one VDD pin
for i, pin in enumerate(["VDD_19", "VDD_32", "VDD_48", "VDD_64"]):
    c = Cn(f"C{90 + i}", "100nF"); v3v3_sys += c[1]; gnd += c[2]
c94 = Cn("C94", "4.7uF", C0603); v3v3_sys += c94[1]; gnd += c94[2]
# VDDA: 100nF + 1uF
c95 = Cn("C95", "100nF");        v3v3_sys += c95[1]; gnd += c95[2]
c96 = Cn("C96", "1uF");          v3v3_sys += c96[1]; gnd += c96[2]
# VBAT tied to VDD: 100nF
c99 = Cn("C99", "100nF");        v3v3_sys += c99[1]; gnd += c99[2]

# VCAP_1 / VCAP_2: 2.2uF each, ESR < 2 ohm
vcap1 = Net("VCAP_1"); vcap2 = Net("VCAP_2")
c97 = Cn("C97", "2.2uF", C0603); vcap1 += u1["VCAP_1"], c97[1]; gnd += c97[2]
c98 = Cn("C98", "2.2uF", C0603); vcap2 += u1["VCAP_2"], c98[1]; gnd += c98[2]

# ----------------------------------------------------------------------------
# 8 MHz HSE crystal on PH0/PH1
# ----------------------------------------------------------------------------
osc_in = Net("OSC_IN"); osc_out = Net("OSC_OUT")
osc_in  += u1["PH0"], y90["1"]
osc_out += u1["PH1"], y90["3"]
gnd += y90["GND"], y90["GND_4"]
c100 = Cn("C100", "20pF"); osc_in  += c100[1]; gnd += c100[2]
c101 = Cn("C101", "20pF"); osc_out += c101[1]; gnd += c101[2]

# ----------------------------------------------------------------------------
# USB-C + ESD (VBUS continues to the power block's USB power path)
# ----------------------------------------------------------------------------
vbus = Net("VBUS"); vbus.drive = Pin.drives.POWER
vbus += j90["VBUS_A4"], j90["VBUS_A9"], j90["VBUS_B4"], j90["VBUS_B9"], u91["VBUS"]
gnd  += j90["GND_A1"], j90["GND_A12"], j90["GND_B1"], j90["GND_B12"], j90["SHIELD"], u91["GND"]
c102 = Cn("C102", "1uF"); vbus += c102[1]; gnd += c102[2]   # ESD-chip reference / VBUS filter

r90 = Rn("R90", "5.1k"); r91 = Rn("R91", "5.1k")             # CC pull-downs: USB-C device
cc1 = Net("USB_CC1"); cc1 += j90["CC1"], r90[1]; gnd += r90[2]
cc2 = Net("USB_CC2"); cc2 += j90["CC2"], r91[1]; gnd += r91[2]

usb_dp = Net("USB_DP"); usb_dn = Net("USB_DN")
usb_dp += u1["PA12"], j90["DP_A6"], j90["DP_B6"], u91["IO1"], u91["IO1_6"]
usb_dn += u1["PA11"], j90["DN_A7"], j90["DN_B7"], u91["IO2"], u91["IO2_4"]

# ----------------------------------------------------------------------------
# Boot: BOOT0 button (DFU) and BOOT1 pull-down
# ----------------------------------------------------------------------------
stm_boot0 = Net("STM_BOOT0")            # dual-boot block: 10k pull-down + ESP32-S3 GPIO41
stm_boot0 += u1["BOOT0"]
r92 = Rn("R92", "1k")                   # protects ESP32-S3 GPIO41 when the button is held
btn = Net("BOOT_BTN"); btn += sw90["A"], r92[1]
stm_boot0 += r92[2]
v3v3_sys  += sw90["B"]

r93 = Rn("R93", "10k")                  # PB2/BOOT1 low: system-memory boot when BOOT0 = 1
boot1 = Net("BOOT1"); boot1 += u1["PB2"], r93[1]; gnd += r93[2]

stm_nrst = Net("STM_NRST")              # dual-boot block: 100nF + ESP32-S3 GPIO42 (open drain)
stm_nrst += u1["NRST"]

# ----------------------------------------------------------------------------
# SWD pads + status LED
# ----------------------------------------------------------------------------
swdio = Net("SWDIO"); swdio += u1["PA13"], j91["SWDIO"]
swclk = Net("SWCLK"); swclk += u1["PA14"], j91["SWCLK"]
stm_nrst += j91["NRST"]
v3v3_sys += j91["3V3"]; gnd += j91["GND"]

r94 = Rn("R94", "1k")                   # LED0 (Betaflight), active low
led = Net("LED0_K"); led += d90["K"], u1["PB9"]
led_a = Net("LED0_A"); led_a += d90["A"], r94[1]; v3v3_sys += r94[2]

# ----------------------------------------------------------------------------
# Other blocks' signals: tie the REAL pins to each block's net names
# ----------------------------------------------------------------------------
BLOCK_NETS = {
    # dual-boot (hardware/dual-boot)
    "PC13": "MODE_SENSE", "PB12": "ESP_EN", "PA9": "BRIDGE_TX", "PA10": "BRIDGE_RX",
    # gyro (hardware/gyro)
    "PA5": "GYRO_SCK", "PA6": "GYRO_MISO", "PA7": "GYRO_MOSI",
    "PA4": "GYRO_CS", "PC4": "GYRO_INT",
    # baro (hardware/baro)
    "PB6": "I2C1_SCL", "PB7": "I2C1_SDA",
    # receiver port (hardware/elrs)
    "PA2": "CRSF_TX_MCU", "PA3": "CRSF_RX_MCU",
    # motors (hardware/motors)
    "PB0": "M1_PWM", "PB1": "M2_PWM", "PB4": "M3_PWM", "PB5": "M4_PWM",
    # power (hardware/power)
    "PC1": "VBAT_SENSE",
    # buzzer (hardware/buzzer)
    "PB8": "BEEPER",
    # expansion headers (hardware/expansion)
    "PB10": "UART3_TX", "PB11": "UART3_RX", "PA8": "LED_STRIP",
    "PC6": "PWM1", "PC7": "PWM2", "PC8": "PWM3", "PC9": "PWM4",
}
for pin, net in BLOCK_NETS.items():
    n = Net(net); n += u1[pin]
    n.do_erc = False        # other end lives in that block's netlist (merged by name)

# Every remaining GPIO is free (expansion) - mark explicitly unconnected.
used = set(BLOCK_NETS) | {"PH0", "PH1", "PA11", "PA12", "PA13", "PA14", "PB2",
                          "PB9", "BOOT0", "NRST", "VCAP_1", "VCAP_2"} | POWER_PINS
for n, name in LQFP64.items():
    if name not in used:
        u1[name].func = T.NOCONNECT

# ----------------------------------------------------------------------------
# Checks + output
# ----------------------------------------------------------------------------
ERC()
generate_netlist(tool=KICAD8, file_="stm32.net")
print(">>> wrote stm32.net")
