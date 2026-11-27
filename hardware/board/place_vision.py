"""
DroneKit Pro - place the parts of the vision (top) board.

Run with KiCad's own Python, after build_pcb.py vision:

    "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" place_vision.py

It rewrites the part positions in vision.kicad_pcb (nothing else), using the
engine in placer.py: FIXED parts first, then each NEAR part as close as it
fits to its anchor pad, then every other part next to the pin it serves.

Layout plan (see README.md, "vision placement"):
  top    the ESP32-S3-WROOM-1 module, antenna over the rear edge (1.4 mm past
         it), turned so its camera pins face the front edge, its USB / EN /
         power pins face the board-to-board socket and its IO38-40, UART0
         and bridge pins face the left edge; the ESP I2C (J134) and ESP IO
         (J135) JST ports on the front edge; the boot-mode switch SW1, the
         ESP program button SW2 and the UART0 pads J1 along the left edge,
         where they can be reached from above.
  bottom (faces the fc board's top, ~5 mm away) the camera FPC on the front
         edge, the PWM (J133) and LED-strip (J132) JST ports on the left edge,
         the AP7361C 3.3 V LDO and the camera LDOs, and the small parts.

The antenna keep-out (no copper on any layer) covers the rear strip,
x < -11.4 mm, between the two rear mounting holes; the engine keeps parts
out of it.

Height under the vision board: its bottom-side parts sit over the fc board's
top-side parts, with the header + socket gap (about 5 mm) between the boards.
  - FPC J30 (2.0 mm) is over fc's JST J130/J131 (2.95 mm): 4.95 mm.
  - JSTs J133/J132 (2.95 mm) are over fc's crystal, LDO, baro and caps
    (1.2 mm at most).
  - Nothing taller than a 0603 sits over fc's USB-C (3.3 mm, x < -7.1 mm,
    |y| < 5.4 mm); most of that area is the antenna keep-out anyway.
"""

import os

from placer import TOP, BOT, run

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "vision.kicad_pcb")
SILK_LABELS = {"U2", "J1", "J30", "J132", "J133", "J134", "J135", "J201", "SW1", "SW2"}
EDGE_OVERHANG = {"U2": 1.7}          # antenna end 1.4 mm past the rear edge (+ courtyard)

# ---------------------------------------------------------------------------
# 1. Fixed parts: ref -> (side, x, y, rotation) or (side, "edge", edge, along)
# ---------------------------------------------------------------------------
FIXED = {
    # --- top
    "U2":   (TOP, -4.65, 0.0, 90),         # module; antenna end at x = -17.4, keep-out fits between the rear holes
    "J134": (TOP, "edge", "+x", -6.0),     # ESP I2C port
    "J135": (TOP, "edge", "+x", 3.9),      # ESP IO port
    "SW1":  (TOP, -3.0, -12.4, 0),         # boot-mode slide switch (Copal CHS-01A)
    "SW2":  (TOP, 4.5, -12.4, 0),          # ESP program button (KMR2), near IO0
    # --- bottom
    "J30":  (BOT, "edge", "+x", 0.4),      # camera FPC, centred on the camera pins
    "J133": (BOT, "edge", "-y", -5.9),     # PWM port (clear of the antenna keep-out)
    "J132": (BOT, "edge", "-y", 3.0),      # LED-strip port (clear of the FPC)
}

# ---------------------------------------------------------------------------
# 2. Anchors for the rest, in this order: ref -> (side, anchor, other_ok)
# ---------------------------------------------------------------------------
NEAR = {
    # ESP32-S3 supply: AP7361C under the module, clear of fc's USB-C
    "U12": (BOT, (-1.0, 4.5), False),
    "C19": (BOT, "U12.1", False), "C20": (BOT, "U12.3", False),
    "C1":  (BOT, "U2.2", True),
    # ESP32-S3 EN and straps, at their pins
    "R2": (TOP, "U2.3", True), "C3": (TOP, "U2.3", True),
    "R4": (TOP, "U2.27", True), "R5": (TOP, "U2.26", True), "R6": (TOP, "U2.16", True),
    "J1": (TOP, "U2.37", True),                     # UART0 recovery pads
    # boot-mode switch parts
    "R1": (TOP, "SW1.1", True), "C2": (TOP, "SW1.1", True),
    # camera: LDOs and caps next to the FPC, on its side
    "U30": (BOT, (8.0, -6.0), True), "U31": (BOT, (8.0, 6.0), True),
    "C30": (BOT, "U30.3", True), "C31": (BOT, "U30.2", True),
    "C32": (BOT, "U31.3", True), "C33": (BOT, "U31.2", True),
    "C34": (BOT, "J30.1", True), "C35": (BOT, "J30.1", True), "C36": (BOT, "J30.1", True),
    "R30": (BOT, "J30.1", True), "R33": (BOT, "J30.1", True), "C37": (BOT, "J30.1", True),
    "R31": (TOP, "U2.4", True), "R32": (TOP, "U2.5", True),
    # ESP I2C pull-ups at the module, series resistors at the ports
    "R141": (TOP, "U2.24", True), "R142": (TOP, "U2.25", True),
    "R139": (TOP, "J134.3", True), "R140": (TOP, "J134.4", True), "C134": (TOP, "J134.2", True),
    "C135": (TOP, "J135.2", True),
    "R134": (BOT, "J132.3", True), "C132": (BOT, "J132.2", True),
    "C133": (BOT, "J133.2", True),
}

if __name__ == "__main__":
    run(PCB, FIXED, NEAR, SILK_LABELS, EDGE_OVERHANG)
