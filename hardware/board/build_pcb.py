"""
DroneKit Pro - start the PCB of one of the two stacked boards.

Run with KiCad's own Python (it needs the pcbnew module):

    "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" build_pcb.py fc
    "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" build_pcb.py vision

Asks KiCad (kicad-cli) for the netlist of <board>.kicad_sch (written by
build_board.py), so net names, symbol links and fields are exactly what
KiCad's "Update PCB from Schematic" and DRC parity check expect, then writes
<board>.kicad_pcb with:

  - 4 copper layers (F.Cu, In1.Cu GND, In2.Cu power, B.Cu); fc 1.6 mm, vision 1.0 mm.
  - Edge.Cuts: 32 x 30 mm, 2 mm corner radius, centred on ORIGIN
    (same as hardware/mechanical/fc_pcb_outline.dxf; +X = front/camera).
  - H1-H4: M1.4 mounting holes on a 25.5 mm square (board-only parts).
  - The board-to-board pair placed so its pins line up through the stack:
    J200 (male header) on top of fc at B2B_AT, J201 (female socket) on the
    bottom of vision with every pad on the same XY as J200's pad of the
    same number.
  - Every schematic part with its footprint, value and pad nets.
  - Design rules inside JLCPCB's 4-layer capability: 0.1 mm track and
    clearance, 0.45/0.2 mm vias. KiCad keeps these in <board>.kicad_pro, so
    this script writes them there too.

The other parts are NOT placed: they're parked beside the board in one
column per block, the same as KiCad's "Update PCB from Schematic".

Re-running this script overwrites <board>.kicad_pcb, including any placement
done in KiCad. Once placement starts in KiCad, use
Tools -> Update PCB from Schematic instead of this script.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
KICAD = "C:/Program Files/KiCad/10.0"
KICAD_FP = KICAD + "/share/kicad/footprints"
KICAD_CLI = KICAD + "/bin/kicad-cli.exe"
LOCAL_LIBS = {"dronekit": os.path.join(HERE, "dronekit.pretty")}

ORIGIN = (150.0, 100.0)          # board centre on the KiCad page, mm
BOARD_W, BOARD_H, CORNER_R = 32.0, 30.0, 2.0
HOLE_PITCH = 25.5

# Ref-number ranges per block (hardware/README.md). Refs below 10 are the
# dual-boot block (ESP32-S3 module, its passives, boot switches, UART pads).
BLOCKS = [
    ("power",      10, 29),
    ("camera",     30, 39),
    ("motors",     40, 59),
    ("receiver",   60, 69),
    ("baro",       70, 79),
    ("gyro",       80, 89),
    ("stm32",      90, 119),
    ("buzzer",    120, 129),
    ("expansion", 130, 159),
]


def mm(v):
    return pcbnew.FromMM(v)


def pt(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))


def block_of(ref):
    n = int(re.search(r"\d+", ref).group())
    for name, lo, hi in BLOCKS:
        if lo <= n <= hi:
            return name
    return "dual-boot"


def sexpr(text):
    """Minimal S-expression reader: returns nested lists of strings."""
    tokens = re.findall(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()]+', text)
    stack = [[]]
    for tok in tokens:
        if tok == "(":
            stack.append([])
        elif tok == ")":
            done = stack.pop()
            stack[-1].append(done)
        else:
            stack[-1].append(tok[1:-1].replace('\\"', '"') if tok.startswith('"') else tok)
    return stack[0][0]


def child(node, key):
    return next((c for c in node[1:] if isinstance(c, list) and c and c[0] == key), None)


def children(node, key):
    return [c for c in node[1:] if isinstance(c, list) and c and c[0] == key]


def read_netlist(name):
    """KiCad's own netlist of <name>.kicad_sch.
    Returns comps [(ref, value, footprint, symbol_uuid, {field: value})]
    and nets {name: [(ref, pin)]}."""
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "board.net")
        subprocess.run([KICAD_CLI, "sch", "export", "netlist", "-o", out,
                        os.path.join(HERE, f"{name}.kicad_sch")],
                       check=True, capture_output=True)
        tree = sexpr(open(out, encoding="utf8").read())
    comps = []
    for c in children(child(tree, "components"), "comp"):
        fields = {f[1][1]: (f[2] if len(f) > 2 else "")
                  for f in children(child(c, "fields"), "field")}
        comps.append((child(c, "ref")[1], child(c, "value")[1],
                      child(c, "footprint")[1], child(c, "tstamps")[1], fields))
    nets = {}
    for n in children(child(tree, "nets"), "net"):
        nets[child(n, "name")[1]] = [(child(x, "ref")[1], child(x, "pin")[1])
                                     for x in children(n, "node")]
    return comps, nets


def load_fp(fpid):
    lib, name = fpid.split(":")
    path = LOCAL_LIBS.get(lib, f"{KICAD_FP}/{lib}.pretty")
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None:
        raise SystemExit(f"footprint not found: {fpid}")
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


def edge_cuts(board):
    x0, y0 = ORIGIN
    hw, hh, r = BOARD_W / 2, BOARD_H / 2, CORNER_R

    def seg(a, b):
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pt(x0 + a[0], y0 + a[1])); s.SetEnd(pt(x0 + b[0], y0 + b[1]))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1)); board.Add(s)

    def arc(cx, cy, sx, sy):  # 90 deg arc around (cx, cy) starting at (sx, sy)
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_ARC)
        s.SetCenter(pt(x0 + cx, y0 + cy)); s.SetStart(pt(x0 + sx, y0 + sy))
        s.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(90, pcbnew.DEGREES_T))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1)); board.Add(s)

    seg((-hw + r, -hh), (hw - r, -hh))
    seg((hw, -hh + r), (hw, hh - r))
    seg((hw - r, hh), (-hw + r, hh))
    seg((-hw, hh - r), (-hw, -hh + r))
    arc(hw - r, -hh + r, hw - r, -hh)
    arc(hw - r, hh - r, hw, hh - r)
    arc(-hw + r, hh - r, -hw + r, hh)
    arc(-hw + r, -hh + r, -hw, -hh + r)


RULES = {  # mm; JLCPCB 4-layer standard capability, with margin
    "min_clearance": 0.1,
    "min_track_width": 0.1,
    "min_via_diameter": 0.45,
    "min_via_annular_width": 0.1,
    "min_through_hole_diameter": 0.2,
    "min_hole_clearance": 0.2,
    "min_hole_to_hole": 0.25,
    "min_copper_edge_clearance": 0.25,
    "min_silk_clearance": 0.0,
}
DEFAULT_CLASS = {"name": "Default", "clearance": 0.1, "track_width": 0.15,
                 "via_diameter": 0.45, "via_drill": 0.2,
                 "microvia_diameter": 0.3, "microvia_drill": 0.1,
                 "diff_pair_width": 0.15, "diff_pair_gap": 0.15, "diff_pair_via_gap": 0.25,
                 "wire_width": 6, "bus_width": 12, "line_style": 0,
                 "pcb_color": "rgba(0, 0, 0, 0.000)",
                 "schematic_color": "rgba(0, 0, 0, 0.000)", "priority": 2147483647}


THICKNESS = {"fc": 1.6, "vision": 1.0}     # mm; vision is lighter, carries no motor current


def design_rules(board, thickness):
    ds = board.GetDesignSettings()
    ds.m_TrackMinWidth = mm(RULES["min_track_width"])
    ds.m_MinClearance = mm(RULES["min_clearance"])
    ds.m_ViasMinSize = mm(RULES["min_via_diameter"])
    ds.m_MinThroughDrill = mm(RULES["min_through_hole_diameter"])
    ds.m_CopperEdgeClearance = mm(RULES["min_copper_edge_clearance"])
    ds.m_HoleClearance = mm(RULES["min_hole_clearance"])
    ds.SetBoardThickness(mm(thickness))


def write_project_rules(name):
    """KiCad reads design rules and net classes from the .kicad_pro file."""
    path = os.path.join(HERE, f"{name}.kicad_pro")
    pro = json.load(open(path, encoding="utf8"))
    pro.setdefault("board", {}).setdefault("design_settings", {})["rules"] = RULES
    pro["net_settings"] = {"classes": [DEFAULT_CLASS], "meta": {"version": 4},
                           "net_colors": None, "netclass_assignments": None,
                           "netclass_patterns": []}
    with open(path, "w", encoding="utf8", newline="\n") as f:
        json.dump(pro, f, indent=2)
        f.write("\n")


# Board-to-board header: centre of its pads, rotation. Same on both boards
# (both seen from the top), so pin N on fc sits under pin N on vision. It runs
# along X at the board's +Y edge (KiCad +y = right side looking forward),
# between the mounting holes.
B2B_REFS = ("J200", "J201")
B2B_AT = (0.0, 11.6, 90)


def b2b_targets():
    """Pad number -> XY of J200 (fc's header) at B2B_AT. J201 must match."""
    fp = load_fp("Connector_PinHeader_1.27mm:PinHeader_2x12_P1.27mm_Vertical")
    fp.SetOrientationDegrees(B2B_AT[2])
    bb = None
    for pad in fp.Pads():
        if bb is None:
            bb = pad.GetBoundingBox()
        else:
            bb.Merge(pad.GetBoundingBox())
    shift = pt(ORIGIN[0] + B2B_AT[0], ORIGIN[1] + B2B_AT[1]) - bb.GetCenter()
    return {pad.GetNumber(): pad.GetPosition() + shift for pad in fp.Pads()}


def place_b2b(fp, ref):
    """J200: header on top of fc. J201: socket on the BOTTOM of vision.
    Either way, every pad lands on the same XY as J200's pad of that number."""
    want = b2b_targets()
    if ref == "J201":
        fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    for rot in (0, 90, 180, 270):
        fp.SetOrientationDegrees(rot)
        p1 = next(p for p in fp.Pads() if p.GetNumber() == "1")
        fp.SetPosition(fp.GetPosition() + want["1"] - p1.GetPosition())
        if all((p.GetPosition() - want[p.GetNumber()]).EuclideanNorm() < mm(0.001)
               for p in fp.Pads()):
            return
    raise SystemExit(f"{ref}: no rotation puts every pad on J200's pad positions")


# Pads joined inside the part, so DRC counts a connection through them.
# USBLC6-2SC6: I/O1 is pins 1 and 6, I/O2 pins 3 and 4 (flow-through).
JUMPER_PADS = {"U91": [("1", "6"), ("3", "4")]}


def add_jumper_pads(path):
    """pcbnew's Python can't set a footprint's jumper pad groups, so write
    them into the saved file (KiCad keeps them on every later save)."""
    s = open(path, encoding="utf8").read()
    for ref, groups in JUMPER_PADS.items():
        i = s.find(f'(property "Reference" "{ref}"')
        if i < 0:
            continue                                # part is on the other board
        start = s.rfind("\n\t(footprint ", 0, i)
        line_end = s.find("\n", start + 1)
        text = " ".join("(" + " ".join(f'"{p}"' for p in g) + ")" for g in groups)
        s = s[:line_end] + f"\n\t\t(jumper_pad_groups {text})" + s[line_end:]
    open(path, "w", encoding="utf8", newline="").write(s)


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else ""
    if name not in ("fc", "vision"):
        raise SystemExit("usage: build_pcb.py fc|vision")
    comps, nets = read_netlist(name)

    board = pcbnew.BOARD()
    board.SetCopperLayerCount(4)
    board.SetLayerName(pcbnew.In1_Cu, "In1.Cu")
    board.SetLayerName(pcbnew.In2_Cu, "In2.Cu")
    design_rules(board, THICKNESS[name])
    edge_cuts(board)

    netinfo = {}
    for net_name in nets:
        n = pcbnew.NETINFO_ITEM(board, net_name)
        board.Add(n)
        netinfo[net_name] = n
    pad_net = {(r, p): n for n, nodes in nets.items() for r, p in nodes}

    # Park parts beside the board: one column per block, right of the board.
    columns = {}
    for ref, value, fpid, uuid, fields in sorted(
            comps, key=lambda c: (block_of(c[0]), int(re.search(r"\d+", c[0]).group()))):
        fp = load_fp(fpid)
        fp.SetReference(ref)
        fp.SetValue(value)
        fp.SetPath(pcbnew.KIID_PATH("/" + uuid))
        for field, text in fields.items():
            if field not in ("Footprint", "Datasheet", "Description"):
                fp.SetField(field, text)
                fp.GetField(field).SetVisible(False)
        for pad in fp.Pads():
            n = pad_net.get((ref, pad.GetNumber()))
            if n:
                pad.SetNet(netinfo[n])
        if ref in B2B_REFS:
            board.Add(fp)
            place_b2b(fp, ref)
            fp.SetLocked(True)
            continue
        columns.setdefault(block_of(ref), []).append(fp)

    x = ORIGIN[0] + BOARD_W / 2 + 15
    for block in [b[0] for b in BLOCKS] + ["dual-boot"]:
        fps = columns.get(block, [])
        if not fps:
            continue
        y = ORIGIN[1] - BOARD_H / 2
        widest = 0.0
        txt = pcbnew.PCB_TEXT(board)
        txt.SetText(block.upper()); txt.SetLayer(pcbnew.Cmts_User)
        txt.SetPosition(pt(x, y - 4)); txt.SetTextSize(pt(1.5, 1.5)); board.Add(txt)
        for fp in fps:
            board.Add(fp)
            # extent = body, both courtyards and any keep-out zone (U2 antenna)
            bb = fp.GetBoundingBox(False)
            for side in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
                c = fp.GetCourtyard(side)
                if c.OutlineCount():
                    bb.Merge(c.BBox())
            for z in fp.Zones():
                bb.Merge(z.GetBoundingBox())
            w, h = pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())
            off = fp.GetPosition() - bb.GetCenter()   # anchor vs extent centre
            fp.SetPosition(pt(x + w / 2, y + h / 2) + off)
            y += h + 1.5
            widest = max(widest, w)
        x += widest + 6

    # Mounting holes (board-only parts, no schematic symbol).
    for i, (sx, sy) in enumerate([(-1, -1), (1, -1), (1, 1), (-1, 1)]):
        h = load_fp("dronekit:MountingHole_1.6mm_M1.4")
        h.SetReference(f"H{i + 1}")
        h.SetValue("M1.4")
        h.SetAttributes(h.GetAttributes() | pcbnew.FP_BOARD_ONLY)
        h.SetPosition(pt(ORIGIN[0] + sx * HOLE_PITCH / 2, ORIGIN[1] + sy * HOLE_PITCH / 2))
        board.Add(h)

    out = os.path.join(HERE, f"{name}.kicad_pcb")
    board.Save(out)
    add_jumper_pads(out)
    write_project_rules(name)
    print(f">>> wrote {name}.kicad_pcb: {len(comps)} parts + 4 holes, {len(nets)} nets, "
          f"{BOARD_W:g} x {BOARD_H:g} mm, 4 layers")


if __name__ == "__main__":
    main()
