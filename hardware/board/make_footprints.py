"""
DroneKit Pro - custom footprints that KiCad 10 doesn't ship.

Writes dronekit.pretty/*.kicad_mod. Run: python make_footprints.py

TI_RNM0015A_VQFN-HR-15_2.5x3mm_P0.5mm  (TPS63070RNM, U10)
  From TI SLVSC58B (rev. March 2019), RNM0015A drawing 4222000/B:
  page 39 package outline, page 40 example board layout (20x).
  Origin = package centre, pin 1 top-left, KiCad +y down.
    pads 1-4   (left)  0.60 x 0.25, x = -1.15, y = -0.75 .. +0.75, pitch 0.5
    pads 15,14 (top)   0.25 x 0.60, x = -0.725 / -0.225, y = -1.40
    pads 5,6   (bot)   0.25 x 0.60, x = -0.725 / -0.225, y = +1.40
    pads 13/12 (top, VIN) and 7/8 (bottom, VOUT): one U-shaped land each,
      0.75 wide x 0.60 tall, centred x = +0.525; two 0.25 legs with a
      0.25 x 0.35 notch between them on the outer side. Built here as one
      leg pad per pin plus a 0.75 x 0.25 bridge pad (numbered like the
      first leg) on the inner side. The legs of each U share a net
      (VIN, VOUT), so the overlap is intended.
    pad 11 (L1)  1.35 x 0.25 at (+0.775, -0.5)
    pad 10 (PGND) 1.70 x 0.25 at (+0.600,  0.0)
    pad 9  (L2)  1.35 x 0.25 at (+0.775, +0.5)
  Body 2.5 x 3.0 mm, 1.0 mm max height.
  Re-check against TI's current drawing before ordering boards.

SolderPads_1xNN_*  (battery, motor, buzzer, receiver, SWD, ESP UART0 pads)
  Plain SMD pads for soldering wires, replacing the pin-header placeholders.
  No paste layer: these are hand-soldered after assembly.

ESP32-S3-WROOM-1_BoardEdge  (U2, vision board)
  KiCad's module footprint with a body-only courtyard and the antenna
  keep-out trimmed to stop short of the rear mounting holes. Generated
  from KiCad 10's own footprint file.

MountingHole_1.6mm_M1.4  (H1-H4, board-only)
  1.6 mm NPTH with a 3.6 mm courtyard on both sides (the cage's standoff
  bosses need a 3.5 mm keep-out; hardware/mechanical/README.md).
"""
import os
import re
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dronekit.pretty")

def pad(num, x, y, w, h):
    return (f'\t(pad "{num}" smd roundrect (at {x:.4f} {y:.4f}) (size {w:.4f} {h:.4f}) '
            f'(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.2))\n')

def line(x1, y1, x2, y2, layer, w):
    return (f'\t(fp_line (start {x1} {y1}) (end {x2} {y2}) '
            f'(stroke (width {w}) (type solid)) (layer "{layer}"))\n')

def rect(x1, y1, x2, y2, layer, w):
    return (line(x1, y1, x2, y1, layer, w) + line(x2, y1, x2, y2, layer, w) +
            line(x2, y2, x1, y2, layer, w) + line(x1, y2, x1, y1, layer, w))

def rnm0015a():
    name = "TI_RNM0015A_VQFN-HR-15_2.5x3mm_P0.5mm"
    s = (f'(footprint "{name}"\n\t(version 20240108)\n\t(generator "dronekit_make_footprints")\n'
         f'\t(layer "F.Cu")\n'
         f'\t(descr "TI RNM0015A VQFN-HR 15 pin 2.5x3mm, TPS63070RNM (SLVSC58B p.39-40, drawing 4222000/B)")\n'
         f'\t(tags "VQFN-HR RNM0015A TPS63070")\n\t(attr smd)\n'
         f'\t(property "Reference" "REF**" (at 0 -2.6 0) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))\n'
         f'\t(property "Value" "{name}" (at 0 2.6 0) (layer "F.Fab") (effects (font (size 0.5 0.5) (thickness 0.08))))\n')
    for i, y in enumerate((-0.75, -0.25, 0.25, 0.75)):      # pins 1-4
        s += pad(i + 1, -1.15, y, 0.60, 0.25)
    s += pad(15, -0.725, -1.40, 0.25, 0.60)
    s += pad(14, -0.225, -1.40, 0.25, 0.60)
    s += pad(5,  -0.725, +1.40, 0.25, 0.60)
    s += pad(6,  -0.225, +1.40, 0.25, 0.60)
    # VIN U (top): legs 13 (left) and 12 (right), bridge on the inner (lower) side
    s += pad(13, 0.275, -1.40, 0.25, 0.60)
    s += pad(12, 0.775, -1.40, 0.25, 0.60)
    s += pad(13, 0.525, -1.225, 0.75, 0.25)
    # VOUT U (bottom): legs 7 (left) and 8 (right), bridge on the inner (upper) side
    s += pad(7, 0.275, 1.40, 0.25, 0.60)
    s += pad(8, 0.775, 1.40, 0.25, 0.60)
    s += pad(7, 0.525, 1.225, 0.75, 0.25)
    s += pad(11, 0.775, -0.5, 1.35, 0.25)
    s += pad(10, 0.600,  0.0, 1.70, 0.25)
    s += pad(9,  0.775,  0.5, 1.35, 0.25)
    s += rect(-1.25, -1.5, 1.25, 1.5, "F.Fab", 0.1)
    s += rect(-1.75, -2.0, 1.75, 2.0, "F.CrtYd", 0.05)
    # silk: corner ticks clear of the pads, pin-1 mark
    s += line(-1.36, -1.61, -1.0, -1.61, "F.SilkS", 0.12)
    s += line(1.36, 1.61, 1.0, 1.61, "F.SilkS", 0.12)
    s += line(1.36, -1.61, 1.0, -1.61, "F.SilkS", 0.12)
    s += f'\t(fp_circle (center -1.6 -1.25) (end -1.5 -1.25) (stroke (width 0.12) (type solid)) (fill yes) (layer "F.SilkS"))\n'
    s += ')\n'
    open(os.path.join(OUT, name + ".kicad_mod"), "w", encoding="utf8").write(s)
    return name

def mounting_hole_m14():
    """M1.4 mounting hole: 1.6 mm NPTH, 3.6 mm courtyard on both sides for the
    cage's standoff bosses (hardware/mechanical/README.md: 3.5 mm keep-out)."""
    name = "MountingHole_1.6mm_M1.4"
    s = (f'(footprint "{name}"\n\t(version 20240108)\n\t(generator "dronekit_make_footprints")\n'
         f'\t(layer "F.Cu")\n'
         f'\t(descr "M1.4 mounting hole, 1.6 mm NPTH, 3.6 mm keep-out for standoff bosses")\n'
         f'\t(tags "mounting hole M1.4")\n\t(attr exclude_from_pos_files exclude_from_bom)\n'
         f'\t(property "Reference" "REF**" (at 0 -2.4 0) (layer "F.SilkS") hide (effects (font (size 0.8 0.8) (thickness 0.12))))\n'
         f'\t(property "Value" "{name}" (at 0 2.4 0) (layer "F.Fab") (effects (font (size 0.5 0.5) (thickness 0.08))))\n'
         f'\t(pad "" np_thru_hole circle (at 0 0) (size 1.6 1.6) (drill 1.6) (layers "*.Cu" "*.Mask"))\n')
    for layer in ("F.CrtYd", "B.CrtYd"):
        s += f'\t(fp_circle (center 0 0) (end 1.8 0) (stroke (width 0.05) (type solid)) (fill no) (layer "{layer}"))\n'
    s += '\t(fp_circle (center 0 0) (end 1.75 0) (stroke (width 0.12) (type solid)) (fill no) (layer "F.SilkS"))\n'
    s += ')\n'
    open(os.path.join(OUT, name + ".kicad_mod"), "w", encoding="utf8").write(s)
    return name

SOLDER_PADS = [  # (pins, pitch, pad w, pad h, what for)
    (2, 3.5, 2.5, 3.5, "battery pigtail, 1S/2S (J10)"),
    (2, 2.0, 1.3, 2.0, "motor wires (J40-J43), buzzer (J120)"),
    (3, 1.5, 1.0, 1.8, "ESP32-S3 UART0 recovery (J1)"),
    (4, 1.5, 1.0, 1.8, "receiver port (J60)"),
    (5, 1.5, 1.0, 1.8, "SWD (J91)"),
]


def solder_pads(n, pitch, w, h, what):
    """A row of plain SMD pads for soldering wires (no paste: hand-soldered).
    Pin 1 on the left, pads in a row along X, centred on the origin."""
    name = f"SolderPads_1x{n:02d}_P{pitch:g}mm_{w:g}x{h:g}mm"
    x0 = -(n - 1) * pitch / 2
    cx, cy = (n - 1) * pitch / 2 + w / 2 + 0.25, h / 2 + 0.25
    s = (f'(footprint "{name}"\n\t(version 20240108)\n\t(generator "dronekit_make_footprints")\n'
         f'\t(layer "F.Cu")\n'
         f'\t(descr "{n} wire solder pads, {pitch:g} mm pitch, {w:g} x {h:g} mm: {what}")\n'
         f'\t(tags "solder pads wire")\n\t(attr smd)\n'
         f'\t(property "Reference" "REF**" (at 0 {-cy - 0.8:.3f} 0) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))\n'
         f'\t(property "Value" "{name}" (at 0 {cy + 0.8:.3f} 0) (layer "F.Fab") (effects (font (size 0.5 0.5) (thickness 0.08))))\n')
    for k in range(n):
        shape = "rect" if k == 0 else "roundrect"
        extra = "" if k == 0 else " (roundrect_rratio 0.25)"
        s += (f'\t(pad "{k + 1}" smd {shape} (at {x0 + k * pitch:.4f} 0) (size {w:g} {h:g}) '
              f'(layers "F.Cu" "F.Mask"){extra})\n')
    s += rect(-cx, -cy, cx, cy, "F.CrtYd", 0.05)
    s += rect(-cx + 0.25, -cy + 0.25, cx - 0.25, cy - 0.25, "F.Fab", 0.1)
    s += f'\t(fp_circle (center {x0 - w / 2 - 0.45:.3f} {-h / 2:.3f}) (end {x0 - w / 2 - 0.35:.3f} {-h / 2:.3f}) (stroke (width 0.12) (type solid)) (fill yes) (layer "F.SilkS"))\n'
    s += ')\n'
    open(os.path.join(OUT, name + ".kicad_mod"), "w", encoding="utf8").write(s)
    return name


KICAD_FP = "C:/Program Files/KiCad/10.0/share/kicad/footprints"


def esp32_s3_board_edge():
    """KiCad's ESP32-S3-WROOM-1 with two changes for the vision board, where
    the antenna sits at (and slightly over) the rear edge:
      - the courtyard is the module body only (KiCad's also covers the
        48 x 21 mm antenna clearance area, which made every nearby part a
        courtyard overlap);
      - the copper keep-out beside the antenna is trimmed from +/-24 mm to
        +/-10.9 mm across, so it stops short of the two rear M1.4 holes
        (at +/-12.75 mm). It still bans tracks, vias, pads, pours and parts
        on every layer there. Use nylon screws at those two holes.
    Pads, pins and silkscreen are untouched. Needs KiCad 10 installed."""
    src = f"{KICAD_FP}/RF_Module.pretty/ESP32-S3-WROOM-1.kicad_mod"
    if not os.path.exists(src):
        print("skip ESP32-S3-WROOM-1_BoardEdge: KiCad footprint not found")
        return None
    name = "ESP32-S3-WROOM-1_BoardEdge"
    t = open(src, encoding="utf8").read()
    t = t.replace('(footprint "ESP32-S3-WROOM-1"', f'(footprint "{name}"', 1)
    # drop every F.CrtYd line, add the body rectangle
    t, n = re.subn(r'\n\t\(fp_line\s*\n\t\t\(start [^)]*\)\s*\n\t\t\(end [^)]*\)\s*\n\t\t\(stroke[^)]*\)\s*'
                   r'\(type [^)]*\)\s*\)\s*\n\t\t\(layer "F\.CrtYd"\)\s*\n\t\t\(uuid "[^"]*"\)\s*\n\t\)', '', t)
    if n != 8:
        raise SystemExit(f"ESP32-S3-WROOM-1: expected 8 courtyard lines, found {n}")
    body = rect(-9.75, -13.0, 9.75, 13.45, "F.CrtYd", 0.05)
    t = t.replace('\n\t(fp_line', '\n' + body.rstrip('\n') + '\n\t(fp_line', 1)
    old = "(xy -24 -6.75) (xy 24 -6.75) (xy 24 -27.75) (xy -24 -27.75)"
    if old not in re.sub(r"\s+", " ", t):
        raise SystemExit("ESP32-S3-WROOM-1: keep-out polygon not as expected")
    t = re.sub(r"\(xy -24 -6\.75\)(\s*)\(xy 24 -6\.75\)(\s*)\(xy 24 -27\.75\)(\s*)\(xy -24 -27\.75\)",
               r"(xy -10.9 -6.75)\1(xy 10.9 -6.75)\2(xy 10.9 -27.75)\3(xy -10.9 -27.75)", t)
    t = t.replace('(descr "', '(descr "DroneKit board-edge variant: body-only courtyard, keep-out trimmed to +/-10.9 mm. ', 1)
    open(os.path.join(OUT, name + ".kicad_mod"), "w", encoding="utf8").write(t)
    return name


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    print("wrote", rnm0015a())
    print("wrote", mounting_hole_m14())
    for spec in SOLDER_PADS:
        print("wrote", solder_pads(*spec))
    print("wrote", esp32_s3_board_edge())
