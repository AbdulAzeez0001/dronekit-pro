"""
DroneKit Pro - expansion headers block, as code.

Six small JST-SH (1.0 mm) headers for plug-in modules. Four hang off the
STM32 (flight side, Mode A / Betaflight); two hang off the ESP32-S3 (student
code side, Mode B):

  J130 SENSOR   STM32 I2C1 (shared with the baro)   Qwiic/STEMMA QT pin order
  J131 UART3    STM32 USART3 PB10/PB11              GPS, optical flow, telemetry
  J132 LED      STM32 PA8 (TIM1_CH1)                WS2812 LED strip
  J133 PWM      STM32 PC6-PC9 (TIM8_CH1-4)          servos, gripper, extra outputs
  J134 CODE-I2C ESP32-S3 GPIO47/48                  Qwiic/STEMMA QT pin order
  J135 CODE-IO  ESP32-S3 GPIO21/38/39/40            digital I/O, PWM, one-wire

Design reference: hardware/expansion/expansion-design.md

Decisions encoded here:
  1. Split by MCU. In Mode B the student's code runs on the ESP32-S3, so its
     modules plug into ESP pins directly. Flight add-ons (GPS, flow, LEDs)
     need Betaflight, so they go to the STM32.
  2. Both I2C headers use the Qwiic / STEMMA QT pin order (GND, 3V3, SDA,
     SCL) on a 4-pin JST-SH, so off-the-shelf Qwiic sensors plug straight in.
  3. 3.3 V header power comes from +3V3_ESP (1 A LDO with margin), NOT the
     gyro's +3V3_SYS. +3V8 (no 5 V on the board) feeds the UART, LED and PWM
     headers for modules with their own regulators / WS2812 LEDs.
  4. 100R series resistor on every signal pin: protects MCU pins from
     students' wiring mistakes and hot-plugging.
  5. I2C pull-ups: J130 shares I2C1, whose pull-ups already sit in the baro
     block; J134 gets its own 4.7k pull-ups to +3V3_ESP.
  6. Local 1uF decoupling on each header's power pin.

U1 = the STM32 (same as the stm32 block's U1); U2 = the ESP32-S3 (same as
dual-boot U2). Only the pins used here are listed, with local pin numbers.
Refs are PINNED in a reserved 130-159 range so this block never collides with
any other block.
Run:  python3 expansion.py   ->  writes expansion.net + prints ERC.
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

_ref = {"R": 130, "C": 130}
def Rn(value):
    p = R(value=value); p.ref = f"R{_ref['R']}"; _ref["R"] += 1; return p
def Cn(value):
    p = C(value=value); p.ref = f"C{_ref['C']}"; _ref["C"] += 1; return p

def SH(ref, label, names):
    n = len(names)
    p = Part(name=f"JST_SH_{n}P", tool=SKIDL, ref_prefix="J", dest=TEMPLATE,
             pins=[Pin(num=i + 1, name=nm, func=T.PASSIVE) for i, nm in enumerate(names)]
             )(value=label,
               footprint=f"Connector_JST:JST_SH_SM{n:02d}B-SRSS-TB_1x{n:02d}-1MP_P1.00mm_Horizontal")
    p.ref = ref
    return p

# ----------------------------------------------------------------------------
# MCU stubs (local pin numbers)
# ----------------------------------------------------------------------------
STM_PINS = ["PB6", "PB7", "PB10", "PB11", "PA8", "PC6", "PC7", "PC8", "PC9"]
stm32 = Part(name="STM32F405RGT6", tool=SKIDL, ref_prefix="U", dest=TEMPLATE,
             pins=[Pin(num=1, name="VSS", func=T.PWRIN)] +
                  [Pin(num=2 + i, name=p, func=T.BIDIR) for i, p in enumerate(STM_PINS)]
             )(value="STM32F405RGT6", footprint="Package_QFP:LQFP-64_10x10mm_P0.5mm")
stm32.ref = "U1"

ESP_PINS = ["IO47", "IO48", "IO21", "IO38", "IO39", "IO40"]
esp = Part(name="ESP32-S3-WROOM-1-N8R2", tool=SKIDL, ref_prefix="U", dest=TEMPLATE,
           pins=[Pin(num=1, name="3V3", func=T.PWRIN), Pin(num=2, name="GND", func=T.PWRIN)] +
                [Pin(num=3 + i, name=p, func=T.BIDIR) for i, p in enumerate(ESP_PINS)]
           )(value="ESP32-S3-WROOM-1-N8R2", footprint="RF_Module:ESP32-S3-WROOM-1")
esp.ref = "U2"

# ----------------------------------------------------------------------------
# Power
# ----------------------------------------------------------------------------
v3v3_esp = Net("+3V3_ESP"); v3v3_esp.drive = Pin.drives.POWER   # from power block (AP7361C)
v3v8     = Net("+3V8");     v3v8.drive     = Pin.drives.POWER   # from power block (TPS63070)
gnd      = Net("GND");      gnd.drive      = Pin.drives.POWER
gnd += stm32["VSS"], esp["GND"]
v3v3_esp += esp["3V3"]

def signal(mcu_pin, header_pin, mcu_net, hdr_net):
    """MCU pin -> 100R -> header pin."""
    r = Rn("100R")
    a = Net(mcu_net); a += mcu_pin, r[1]
    b = Net(hdr_net); b += r[2], header_pin
    return a, b

# J130 SENSOR: STM32 I2C1 (pull-ups live in the baro block). Qwiic order.
j130 = SH("J130", "SENSOR_I2C", ["GND", "3V3", "SDA", "SCL"])
gnd += j130["GND"]; v3v3_esp += j130["3V3"]
c = Cn("1uF"); v3v3_esp += c[1]; gnd += c[2]
signal(stm32["PB7"], j130["SDA"], "I2C1_SDA", "EXP_SENSOR_SDA")
signal(stm32["PB6"], j130["SCL"], "I2C1_SCL", "EXP_SENSOR_SCL")

# J131 UART3: GPS / optical flow / telemetry
j131 = SH("J131", "UART3", ["GND", "PWR", "TX", "RX"])
gnd += j131["GND"]; v3v8 += j131["PWR"]
c = Cn("1uF"); v3v8 += c[1]; gnd += c[2]
signal(stm32["PB10"], j131["TX"], "UART3_TX", "EXP_UART3_TX")   # STM32 TX -> module RX
signal(stm32["PB11"], j131["RX"], "UART3_RX", "EXP_UART3_RX")   # STM32 RX <- module TX

# J132 LED: WS2812 strip on PA8 (TIM1_CH1)
j132 = SH("J132", "LED_STRIP", ["GND", "PWR", "DIN"])
gnd += j132["GND"]; v3v8 += j132["PWR"]
c = Cn("1uF"); v3v8 += c[1]; gnd += c[2]
signal(stm32["PA8"], j132["DIN"], "LED_STRIP", "EXP_LED_DIN")

# J133 PWM: TIM8 CH1-4 on PC6-PC9
j133 = SH("J133", "PWM", ["GND", "PWR", "PWM1", "PWM2", "PWM3", "PWM4"])
gnd += j133["GND"]; v3v8 += j133["PWR"]
c = Cn("1uF"); v3v8 += c[1]; gnd += c[2]
for i, pin in enumerate(["PC6", "PC7", "PC8", "PC9"]):
    signal(stm32[pin], j133[f"PWM{i + 1}"], f"PWM{i + 1}", f"EXP_PWM{i + 1}")

# J134 CODE-I2C: ESP32-S3 GPIO47 (SDA) / GPIO48 (SCL), own pull-ups. Qwiic order.
j134 = SH("J134", "CODE_I2C", ["GND", "3V3", "SDA", "SCL"])
gnd += j134["GND"]; v3v3_esp += j134["3V3"]
c = Cn("1uF"); v3v3_esp += c[1]; gnd += c[2]
sda, _ = signal(esp["IO47"], j134["SDA"], "ESP_I2C_SDA", "EXP_CODE_SDA")
scl, _ = signal(esp["IO48"], j134["SCL"], "ESP_I2C_SCL", "EXP_CODE_SCL")
r = Rn("4.7k"); sda += r[1]; v3v3_esp += r[2]
r = Rn("4.7k"); scl += r[1]; v3v3_esp += r[2]

# J135 CODE-IO: ESP32-S3 GPIO21/38/39/40
j135 = SH("J135", "CODE_IO", ["GND", "3V3", "IO21", "IO38", "IO39", "IO40"])
gnd += j135["GND"]; v3v3_esp += j135["3V3"]
c = Cn("1uF"); v3v3_esp += c[1]; gnd += c[2]
for io in ["IO21", "IO38", "IO39", "IO40"]:
    signal(esp[io], j135[io], f"ESP_{io}", f"EXP_CODE_{io}")

ERC()
generate_netlist(tool=KICAD8, file_="expansion.net")
print(">>> wrote expansion.net")
