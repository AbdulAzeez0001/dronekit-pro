"""
DroneKit Pro - dual-boot control subcircuit, as code.

Generates a KiCad-importable netlist for the circuit that lets one board
boot either as a Betaflight flight controller (Mode A) or as a WiFi-
programmable robot (Mode B).

Design reference: hardware/dual-boot/dual-boot-design.md

This is the NOVEL part of the board. The values and topology here encode
the two decisions that an AI schematic generator gets wrong:
  1. ESP32-S3 EN has a pull-DOWN (default OFF / dark-by-default), not the
     usual pull-up. The STM32 boots first and drives EN high only in Mode B.
  2. The STM32 touches ONLY: EN, the UART bridge, and the two flash-control
     lines that originate on the ESP32-S3 side. It NEVER drives the S3
     strapping pins (GPIO0/3/45/46), which carry their own resistors.

The ESP side is an ESP32-S3-WROOM-1-N8R2 (PSRAM for the DVP camera; see
hardware/camera/camera-design.md). Camera pins are reserved there, not here.

Parts are defined with explicit pins (SKIDL tool) so the script runs without
a local KiCad symbol library. When you capture this in KiCad/EasyEDA, map each
net to the real symbol pins and assign footprints (see the BOM in the design
doc). Run:  python3 dual_boot.py   ->  writes dual_boot.net + prints ERC.
"""

from skidl import Part, Pin, Net, SKIDL, KICAD8, TEMPLATE, generate_netlist, ERC, set_default_tool

set_default_tool(SKIDL)
T = Pin.types

# ----------------------------------------------------------------------------
# Reusable passive templates
# ----------------------------------------------------------------------------
R = Part(name="R", tool=SKIDL, ref_prefix="R", dest=TEMPLATE,
         footprint="Resistor_SMD:R_0402_1005Metric",
         pins=[Pin(num=1, name="1", func=T.PASSIVE),
               Pin(num=2, name="2", func=T.PASSIVE)])

C = Part(name="C", tool=SKIDL, ref_prefix="C", dest=TEMPLATE,
         footprint="Capacitor_SMD:C_0402_1005Metric",
         pins=[Pin(num=1, name="1", func=T.PASSIVE),
               Pin(num=2, name="2", func=T.PASSIVE)])

# SPST slide switch for boot mode select
SW = Part(name="SW_SPST", tool=SKIDL, ref_prefix="SW", dest=TEMPLATE,
          footprint="Button_Switch_SMD:SW_SPDT_PCM12",  # verify in KiCad
          pins=[Pin(num=1, name="A", func=T.PASSIVE),
                Pin(num=2, name="B", func=T.PASSIVE)])

# Momentary button to put ESP32 into download mode (pulls GPIO0 low)
BTN = Part(name="SW_PUSH", tool=SKIDL, ref_prefix="SW", dest=TEMPLATE,
           footprint="Button_Switch_SMD:SW_SPST_SKQG_WithStem",  # verify in KiCad
           pins=[Pin(num=1, name="A", func=T.PASSIVE),
                 Pin(num=2, name="B", func=T.PASSIVE)])

# ----------------------------------------------------------------------------
# Active parts - only the pins used by the dual-boot subcircuit are defined.
# ----------------------------------------------------------------------------
stm32 = Part(name="STM32F405RGT6", tool=SKIDL, ref_prefix="U", dest=TEMPLATE,
             pins=[
                 Pin(num=1,  name="VDD",        func=T.PWRIN),
                 Pin(num=2,  name="VSS",        func=T.PWRIN),
                 Pin(num=3,  name="MODE_SENSE", func=T.INPUT),   # e.g. PC4
                 Pin(num=4,  name="ESP_EN",     func=T.OUTPUT),  # e.g. PC5, push-pull
                 Pin(num=5,  name="BRIDGE_TX",  func=T.OUTPUT),  # USART TX
                 Pin(num=6,  name="BRIDGE_RX",  func=T.INPUT),   # USART RX
                 Pin(num=7,  name="BOOT0",      func=T.INPUT),
                 Pin(num=8,  name="NRST",       func=T.INPUT),
             ])(value="STM32F405RGT6", footprint="Package_QFP:LQFP-64_10x10mm_P0.5mm")

# Pin numbers below are local to this script, not module pad numbers.
esp32 = Part(name="ESP32-S3-WROOM-1-N8R2", tool=SKIDL, ref_prefix="U", dest=TEMPLATE,
             pins=[
                 Pin(num=1,  name="3V3",  func=T.PWRIN),
                 Pin(num=2,  name="GND",  func=T.PWRIN),
                 Pin(num=3,  name="EN",   func=T.INPUT),   # CHIP_PU
                 Pin(num=4,  name="IO1",  func=T.INPUT),   # UART1 RX <- bridge TX (GPIO matrix)
                 Pin(num=5,  name="IO2",  func=T.OUTPUT),  # UART1 TX -> bridge RX (not a strap on S3)
                 Pin(num=6,  name="IO0",  func=T.BIDIR),   # strapping (pull-up)
                 Pin(num=7,  name="IO45", func=T.BIDIR),   # strapping (pull-down) VDD_SPI select
                 Pin(num=8,  name="IO46", func=T.BIDIR),   # strapping (pull-down) boot mode
                 Pin(num=9,  name="IO41", func=T.OUTPUT),  # -> STM32 BOOT0
                 Pin(num=10, name="IO42", func=T.OPENCOLL),# -> STM32 NRST (open-drain)
                 Pin(num=11, name="TXD0", func=T.OUTPUT),  # UART0 TX (ROM bootloader / console)
                 Pin(num=12, name="RXD0", func=T.INPUT),   # UART0 RX
             ])(value="ESP32-S3-WROOM-1-N8R2", footprint="RF_Module:ESP32-S3-WROOM-1")

# ----------------------------------------------------------------------------
# Nets
# ----------------------------------------------------------------------------
v3v3_sys = Net("+3V3_SYS"); v3v3_sys.drive = Pin.drives.POWER   # clean: STM32 + sensors
v3v3_esp = Net("+3V3_ESP"); v3v3_esp.drive = Pin.drives.POWER   # ESP32 dedicated rail
gnd  = Net("GND");  gnd.drive  = Pin.drives.POWER

mode_sense = Net("MODE_SENSE")
esp_en     = Net("ESP_EN")
bridge_tx  = Net("BRIDGE_TX")
bridge_rx  = Net("BRIDGE_RX")
stm_boot0  = Net("STM_BOOT0")
stm_nrst   = Net("STM_NRST")

# ----------------------------------------------------------------------------
# Power
# ----------------------------------------------------------------------------
v3v3_sys += stm32["VDD"]
v3v3_esp += esp32["3V3"]
gnd      += stm32["VSS"], esp32["GND"]

c_bulk = C(value="10uF", footprint="Capacitor_SMD:C_0805_2012Metric")  # bulk at ESP32 3V3
v3v3_esp += c_bulk[1]; gnd += c_bulk[2]

# ----------------------------------------------------------------------------
# Boot mode switch:  SPST to GND + 10k pull-up.
# Closed = LOW  = Mode A (Fly).   Open = HIGH = Mode B (Code).
# ----------------------------------------------------------------------------
sw_mode  = SW(value="boot_mode")
r_mode   = R(value="10k")          # pull-up
c_deb    = C(value="100nF")        # debounce
mode_sense += stm32["MODE_SENSE"], sw_mode[1], r_mode[1], c_deb[1]
gnd        += sw_mode[2], c_deb[2]
v3v3_sys   += r_mode[2]   # mode pullup on STM32 rail

# ----------------------------------------------------------------------------
# ESP32 EN gating - default OFF (pull-DOWN). STM32 drives HIGH for Mode B.
# ----------------------------------------------------------------------------
r_en = R(value="10k")              # pull-DOWN: dark-by-default
c_en = C(value="100nF")            # noise / soft start
esp_en += stm32["ESP_EN"], esp32["EN"], r_en[1], c_en[1]
gnd    += r_en[2], c_en[2]

# ----------------------------------------------------------------------------
# UART bridge on S3 UART1 via the GPIO matrix (IO1/IO2, non-strapping). Series 100R optional.
# ----------------------------------------------------------------------------
bridge_tx += stm32["BRIDGE_TX"], esp32["IO1"]
bridge_rx += stm32["BRIDGE_RX"], esp32["IO2"]

# ----------------------------------------------------------------------------
# ESP32 -> STM32 flash control (Mode B only; ESP32 pins high-Z in Mode A).
# ----------------------------------------------------------------------------
r_boot0 = R(value="10k")           # BOOT0 pull-DOWN: normal flash boot by default
stm_boot0 += esp32["IO41"], stm32["BOOT0"], r_boot0[1]
gnd       += r_boot0[2]

c_nrst = C(value="100nF")          # STM32 has internal NRST pull-up
stm_nrst += esp32["IO42"], stm32["NRST"], c_nrst[1]
gnd      += c_nrst[2]

# ----------------------------------------------------------------------------
# ESP32-S3 strapping pins - own resistors. STM32 MUST NOT drive these.
#   IO0  pull-up   (HIGH = SPI flash boot; button pulls low for download)
#   IO45 pull-down (VDD_SPI select: LOW = 3.3V flash/PSRAM; HIGH = 1.8V, boot fails)
#   IO46 pull-down (must be LOW for download mode; IO0=0 + IO46=1 is invalid)
#   IO3  left unconnected (JTAG source select, only read if eFuse says so)
# ----------------------------------------------------------------------------
r_io0  = R(value="10k"); v3v3_esp += r_io0[2];  s_io0  = Net("STRAP_IO0");  s_io0  += esp32["IO0"],  r_io0[1]
r_io45 = R(value="10k"); gnd += r_io45[2];      s_io45 = Net("STRAP_IO45"); s_io45 += esp32["IO45"], r_io45[1]
r_io46 = R(value="10k"); gnd += r_io46[2];      s_io46 = Net("STRAP_IO46"); s_io46 += esp32["IO46"], r_io46[1]

# ESP32-S3 program button: GPIO0 -> GND (press = download mode)
btn_prog = BTN(value="ESP_PROG")
esp32["IO0"] += btn_prog[1]
gnd          += btn_prog[2]

# ----------------------------------------------------------------------------
# ESP32-S3 UART0 pads: factory flashing and recovery.
# Normal flashing is over USB-C in Mode B (native USB via the switch in the
# stm32 block). These pads reach the ROM bootloader with any 3.3V USB-serial
# adapter: hold the program button (IO0), power up in Mode B, run esptool.
# Pads: 1 GND  2 ESP_TXD0 (to adapter RX)  3 ESP_RXD0 (from adapter TX)
# ----------------------------------------------------------------------------
UART_PADS = Part(name="UART0_Pads", tool=SKIDL, ref_prefix="J", dest=TEMPLATE,
                 pins=[Pin(num=1, name="GND", func=T.PASSIVE),
                       Pin(num=2, name="TX",  func=T.PASSIVE),
                       Pin(num=3, name="RX",  func=T.PASSIVE)])
j_uart = UART_PADS(value="ESP_UART0",
                   footprint="Connector_PinHeader_1.27mm:PinHeader_1x03_P1.27mm_Vertical")
gnd += j_uart["GND"]
esp_txd0 = Net("ESP_TXD0"); esp_txd0 += esp32["TXD0"], j_uart["TX"]
esp_rxd0 = Net("ESP_RXD0"); esp_rxd0 += esp32["RXD0"], j_uart["RX"]

# ----------------------------------------------------------------------------
# Checks + output
# ----------------------------------------------------------------------------
ERC()
generate_netlist(tool=KICAD8, file_="dual_boot.net")
print(">>> wrote dual_boot.net")
