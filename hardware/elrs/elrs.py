"""
DroneKit Pro - RC receiver port (ExpressLRS add-on), as code.

The ELRS receiver is OPTIONAL: the kit ships without one, and the student or
user buys any small serial ELRS receiver and solders it to these pads. The
board only provides the port:

    J60 pad 1  GND
    J60 pad 2  PWR    +3V8 (highest rail on the board; there is no 5V)
    J60 pad 3  FC_TX  STM32 PA2 (USART2_TX) -> receiver RX
    J60 pad 4  FC_RX  STM32 PA3 (USART2_RX) <- receiver TX

Betaflight runs it as a serial receiver: CRSF protocol on UART2
(serialrx_provider = CRSF). Not inverted, so the F405 UART takes it directly.

Design reference: hardware/elrs/elrs-design.md

Decisions encoded here:
  1. Serial (CRSF) port, not an onboard SPI radio. No 2.4 GHz RF design on
     this board, and no board space spent on a radio most bench/code users
     (Mode B) don't need. SPI3 is freed for expansion.
  2. Pad order GND, PWR, TX, RX matches the wire order printed on most small
     ELRS receivers, so the four wires go straight across.
  3. 100R series resistors on both UART lines: cheap protection if a
     receiver is soldered on the wrong way round or hot-plugged.
  4. Bulk + HF decoupling right at the pads: a receiver's TX bursts come
     through a thin wire.

U1 here is the SAME STM32F405 as dual-boot U1; only these pins are listed.
Refs are PINNED in a reserved 60-69 range so this block never collides with
dual-boot (auto), power (10-29), camera (30-39) or motors (40-59).
Run:  python3 elrs.py   ->  writes elrs.net + prints ERC.
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

# Receiver solder pads (placeholder footprint: 4 pads at 1.27 mm).
j60 = Part(name="RC_RX_Pads", tool=SKIDL, ref_prefix="J", dest=TEMPLATE,
           pins=[Pin(num=1, name="GND",   func=T.PASSIVE),
                 Pin(num=2, name="PWR",   func=T.PASSIVE),
                 Pin(num=3, name="FC_TX", func=T.PASSIVE),
                 Pin(num=4, name="FC_RX", func=T.PASSIVE)]
           )(value="ELRS_RX", footprint="Connector_PinHeader_1.27mm:PinHeader_1x04_P1.27mm_Vertical")
j60.ref = "J60"

# STM32F405 (same part as dual-boot U1) - USART2 only. Local pin numbers.
stm32 = Part(name="STM32F405RGT6", tool=SKIDL, ref_prefix="U", dest=TEMPLATE,
             pins=[Pin(num=1, name="VSS", func=T.PWRIN),
                   Pin(num=2, name="PA2", func=T.OUTPUT),   # USART2_TX
                   Pin(num=3, name="PA3", func=T.INPUT)]    # USART2_RX
             )(value="STM32F405RGT6", footprint="Package_QFP:LQFP-64_10x10mm_P0.5mm")
stm32.ref = "U1"

# ----------------------------------------------------------------------------
# Nets
# ----------------------------------------------------------------------------
v3v8 = Net("+3V8"); v3v8.drive = Pin.drives.POWER   # from power block (TPS63070)
gnd  = Net("GND");  gnd.drive  = Pin.drives.POWER
gnd += stm32["VSS"]

# Receiver power + decoupling at the pads
v3v8 += j60["PWR"]
gnd  += j60["GND"]
c60 = Cn("C60", "10uF", "Capacitor_SMD:C_0805_2012Metric")
c61 = Cn("C61", "100nF")
v3v8 += c60[1], c61[1]; gnd += c60[2], c61[2]

# UART with series protection
r60 = Rn("R60", "100R"); r61 = Rn("R61", "100R")
tx_mcu = Net("CRSF_TX_MCU"); tx_mcu += stm32["PA2"], r60[1]
tx     = Net("CRSF_TX");     tx     += r60[2], j60["FC_TX"]
rx_mcu = Net("CRSF_RX_MCU"); rx_mcu += stm32["PA3"], r61[1]
rx     = Net("CRSF_RX");     rx     += r61[2], j60["FC_RX"]

# ----------------------------------------------------------------------------
# Checks + output
# ----------------------------------------------------------------------------
ERC()
generate_netlist(tool=KICAD8, file_="elrs.net")
print(">>> wrote elrs.net")
