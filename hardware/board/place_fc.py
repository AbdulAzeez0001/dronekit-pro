"""
DroneKit Pro - place the parts of the fc (bottom, flight-controller) board.

Run with KiCad's own Python, after build_pcb.py fc:

    "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" place_fc.py

It rewrites the part positions in fc.kicad_pcb (nothing else), using the
engine in placer.py, in two passes:

1. FIXED: the parts whose spot is set by the cage or by the layout plan:
   edge connectors, the STM32, the battery and motor pads, the gyro, the
   buck-boost. Coordinates are mm from the board centre, KiCad axes:
   +x = front (camera side), +y = the board's right side looking forward
   (mechanical -Y). "edge" parts are pushed flush to that board edge with
   their opening facing out.
2. NEAR: every other part is put as close as it fits to its ANCHOR: the pad
   it serves (a decoupling cap's IC supply pin, a series resistor's IC pin,
   a gate resistor's FET). The search walks outward in 0.25 mm rings and
   takes the first spot where the courtyard is inside the board and clear
   of every other courtyard, hole keep-out and through-hole pin on that side.

It never overlaps parts: if a part can't be placed within MAX_R of its
anchor on its side (or on the other side when that's allowed), the script
stops and says which. Courtyard overlap is the only rule checked here; run
KiCad's DRC afterwards for the rest.

Layout plan (see README.md, "fc placement"):
  top    STM32 in the middle, turned so its USB / ESP32-S3 / PWM side faces
         the board-to-board header J200 on the right edge; its decoupling
         caps, crystal and boot parts around it; USB-C on the rear edge with
         the ESD chip and USB switch between it and the STM32; the two STM32
         JST-SH ports on the front edge.
  bottom (the only fc side you can reach once the vision board is on top)
         every wire pad: battery on the left edge, the four motors at the
         corners, SWD, receiver and buzzer; each motor's FET, flyback diode
         and gate resistors next to its pads; the gyro near the centre; the
         buck-boost and its caps along the left edge, away from the gyro;
         the BOOT button at the front.
"""

import os

from placer import TOP, BOT, run

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "fc.kicad_pcb")
# Parts whose reference stays printed on the silkscreen: what a builder solders
# or plugs into. Every other reference is hidden (still on the fab layer):
# on a board this dense they'd only overlap.
SILK_LABELS = {"J10", "J40", "J41", "J42", "J43", "J60", "J91", "J120",
               "J90", "J130", "J131", "J200", "SW90", "D90", "U1", "U80"}
EDGE_OVERHANG = {"J90": 0.6}        # USB-C shell sticks out past the edge a little

# ---------------------------------------------------------------------------
# 1. Fixed parts: ref -> (side, x, y, rotation) or (side, "edge", edge, along)
#    rotation in degrees, KiCad convention.
# ---------------------------------------------------------------------------
FIXED = {
    # --- top
    "U1":   (TOP, 1.0, -2.0, 270),        # STM32: pins 33-48 (USB, ESP, PWM) face J200
    "J90":  (TOP, "edge", "-x", 0.0),      # USB-C, rear edge, centred
    "J130": (TOP, "edge", "+x", -4.1),     # sensor I2C port, front edge
    "J131": (TOP, "edge", "+x", 4.1),      # UART3 port, front edge
    # --- bottom: wire pads (motor wires come up from the pods at the corners)
    # M1 rear-right, M2 front-right, M3 rear-left, M4 front-left (KiCad +y = right)
    "J40":  (BOT, -14.0, 8.5, 90),
    "J41":  (BOT, 14.0, 8.5, 90),
    "J42":  (BOT, -14.0, -8.5, 90),
    "J43":  (BOT, 14.0, -8.5, 90),
    "J10":  (BOT, 6.5, -12.75, 0),        # battery pads, left edge: lead comes from the side
    "U80":  (BOT, -1.0, -2.0, 0),          # gyro: near the centre, next to the SPI1 pins
    # buck-boost cluster, ~9 mm from the gyro. On the bottom at rotation 0
    # the TPS63070's L1/L2 pins face +x, VIN faces +y (centre), VOUT faces
    # -y (board edge): inductor to the +x side, input caps above, output
    # caps below, each tight to its pins.
    "U10":  (BOT, -3.6, -10.6, 0),
    "L10":  (BOT, 0.5, -10.6, 90),
    "C12":  (BOT, -3.4, -7.6, 0),          # VIN, smallest first
    "C10":  (BOT, -3.4, -5.6, 0),
    "C11":  (BOT, 0.6, -7.25, 0),
    "C13":  (BOT, -3.6, -13.75, 0),        # VOUT
    "C14":  (BOT, -7.2, -13.75, 0),
    "C15":  (BOT, 0.5, -14.0, 0),
    "SW90": (BOT, 8.6, 0.0, 90),           # STM32 BOOT button (KMR2), front, pressable from below
    # flyback diodes beside their motor pads: upright at the front corners,
    # lying flat at the rear ones to clear the USB-C shell pins (|y| < 5.1)
    "D41":  (BOT, 10.5, 6.9, 90),
    "D43":  (BOT, 10.5, -6.9, 90),
    "D40":  (BOT, -8.95, 7.3, 0),
    "D42":  (BOT, -8.95, -7.3, 0),
    # front FETs between the diode and the board edge
    "Q41":  (BOT, 14.1, 3.9, 90),
    "Q43":  (BOT, 14.1, -3.9, 90),
    # receiver series resistors at U1's UART2 pins: the spots fc was routed
    # with (before placer.py's order was fixed, they depended on the build)
    "R60":  (TOP, -6.3, -6.45, 90),
    "R61":  (TOP, -7.9, -5.9, 0),
}

# ---------------------------------------------------------------------------
# 2. Anchors for the rest, placed in this order: ref -> (side, anchor,
#    other_side_allowed). anchor = "REF.PAD" (that pad's position) or (x, y).
#    Parts not listed get an automatic anchor: the IC/connector/FET pad that
#    shares their first signal net.
# ---------------------------------------------------------------------------
NEAR = {
    # USB path: USB-C -> ESD (U91) -> switch (U92) -> STM32 pins 44/45 / J200
    # pins 7/8. The switch goes left of the U1-J200 band so the band is free
    # for the STM32's escape wires; placed first so the caps fit around it.
    "U92": (TOP, (-4.0, 7.6), True), "U91": (TOP, (-9.5, 7.5), True),
    # the two VCAP caps (0805) would land in that band too, in front of the
    # PWM / USART1 pins: VCAP_1 (pin 31) goes round the corner beside U92,
    # VCAP_2 (pin 47) to the right of the band
    "C97": (TOP, (-6.4, 6.0), True), "C98": (TOP, (6.0, 7.0), True),
    "C103": (TOP, "U92.10", True), "C102": (TOP, "U91.5", True),
    # STM32 decoupling: top, at its supply pins (VDD 1/13/19/32/48/64, VCAP 31/47)
    "C90": (TOP, "U1.1", True), "C99": (TOP, "U1.1", True), "C91": (TOP, "U1.19", True),
    "C92": (TOP, "U1.32", True), "C93": (TOP, "U1.48", True), "C95": (TOP, "U1.64", True),
    "C96": (TOP, "U1.13", True), "C94": (TOP, "U1.1", True),
    "Y90": (TOP, "U1.5", True), "C100": (TOP, "Y90.1", True), "C101": (TOP, "Y90.3", True),
    "C4":  (TOP, "U1.7", True), "R93": (TOP, "U1.28", True),
    "R92": (TOP, "U1.60", True), "R3": (TOP, "U1.60", True),
    "D90": (TOP, "U1.62", True), "R94": (TOP, "D90.2", True),      # status LED
    # gyro parts, bottom, tight
    "C80": (BOT, "U80.8", False), "C81": (BOT, "U80.8", False), "C82": (BOT, "U80.5", False),
    "R80": (BOT, "U80.12", True),
    # buzzer: wire pads and driver together on the bottom, rear-right of centre
    "J120": (BOT, (-5.0, 4.0), False),
    "Q120": (BOT, "J120.2", False), "D120": (BOT, "J120.1", False), "C120": (BOT, "D120.1", False),
    "R120": (BOT, "Q120.1", False), "R121": (BOT, "Q120.1", False),
    # buck-boost: caps tight on VIN (12/13) and VOUT (7/8), feedback near FB (5)
    "C16": (BOT, "U10.3", False), "C17": (BOT, "U10.7", False),
    "R11": (BOT, "U10.5", False), "R12": (BOT, "U10.5", False), "R13": (BOT, "U10.14", False),
    "R14": (BOT, "U10.2", True),
    # input power path: reverse-polarity FET + USB diode next to the battery pads
    "Q10": (BOT, "J10.1", True), "R10": (BOT, "Q10.1", True), "R17": (BOT, "Q10.1", True),
    "D10": (BOT, "Q10.2", True),
    # motor channels: diode and FET next to the pads, gate resistors at the FET
    "Q40": (BOT, "D40.2", False), "Q42": (BOT, "D42.2", False),
    "R40": (BOT, "Q40.1", True), "R44": (BOT, "Q40.1", True),
    "R41": (BOT, "Q41.1", True), "R45": (BOT, "Q41.1", True),
    "R42": (BOT, "Q42.1", True), "R46": (BOT, "Q42.1", True),
    "R43": (BOT, "Q43.1", True), "R47": (BOT, "Q43.1", True),
    "C40": (BOT, "J40.1", True), "C41": (BOT, "J43.1", True),
    # 3.3 V LDO and battery sense
    "U11": (TOP, (-10.0, -9.5), True), "C18": (TOP, "U11.5", True),
    "R15": (TOP, "U1.9", True), "R16": (TOP, "U1.9", True), "C21": (TOP, "U1.9", True),
    # other wire pads, bottom
    "J91": (BOT, (2.0, 7.5), False),       # SWD
    "J60": (BOT, (-9.0, -11.5), False),    # receiver
    "C60": (BOT, "J60.2", True), "C61": (BOT, "J60.2", True),
    "C130": (TOP, "J130.2", True), "C131": (TOP, "J131.2", True),
    # port series resistors at the port pins (J130: 3 SDA, 4 SCL; J131: 3 TX, 4 RX)
    "R130": (TOP, "J130.3", True), "R131": (TOP, "J130.4", True),
    "R132": (TOP, "J131.3", True), "R133": (TOP, "J131.4", True),
    # baro: top rear-left corner, under the vision board, out of the props' air
    "U70": (TOP, (-11.0, -12.0), True), "C70": (TOP, "U70.8", True), "C71": (TOP, "U70.6", True),
    "R70": (TOP, "U70.8", True), "R71": (TOP, "U70.8", True),
}


# ---------------------------------------------------------------------------
# 3. Turned in place after placement, by this many degrees. 180 deg keeps the
#    courtyard on the same spot, so no other part moves.
# ---------------------------------------------------------------------------
TURN = {
    # baro cap: at the search's 90 deg its +3V3 / GND pads face U70's GND /
    # +3V3 pins, the two wires have to cross, and no via fits (J42's pad is
    # underneath)
    "C71": 180,
    # buck-boost VAUX cap: at 90 deg its VAUX pad faces U10's GND / PG pins
    # and its GND pad faces VAUX (U10.3); with the power tracks routed first
    # there is no way round
    "C16": 180,
}


def turn(pcb, turns):
    import pcbnew
    board = pcbnew.LoadBoard(pcb)
    for ref, deg in turns.items():
        fp = board.FindFootprintByReference(ref)
        fp.SetOrientationDegrees((fp.GetOrientationDegrees() + deg) % 360)
    board.Save(pcb)


if __name__ == "__main__":
    run(PCB, FIXED, NEAR, SILK_LABELS, EDGE_OVERHANG)
    turn(PCB, TURN)
