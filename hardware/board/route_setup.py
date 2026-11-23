"""
DroneKit Pro - net classes and copper planes for routing one board.

Run with KiCad's own Python, after placement:

    "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" route_setup.py fc
    "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" route_setup.py vision

1. Net classes (written into <board>.kicad_pro, where KiCad keeps them):

   class   track  via        nets                       why
   Motor   0.80   0.60/0.30  battery input, motor M-    ~2.5 A per 720 motor, ~10 A total
   Power   0.40   0.60/0.30  VBAT, +3V8, VBUS, L1/L2,   up to ~1.5 A (buck-boost, USB in)
                             ground stubs
   Rail    0.30   0.45/0.20  3.3 V / camera rails       < 0.5 A
   USB     0.20   0.45/0.20  USB D+/D- pairs            90 ohm-ish pair, 0.15 mm gap
   Default 0.15   0.45/0.20  everything else            signals

   Outer copper is 1 oz. 0.8 mm carries ~2.5 A for a ~10 C rise. The
   battery input and the motor M+ side also get bottom-layer copper pours
   (below), so the 10 A total doesn't run through one track.

2. Copper zones (any previous ones from this script are replaced):

   fc:     In1.Cu GND (whole board)       In2.Cu +3V3_SYS (whole board)
           F.Cu GND fill, B.Cu GND fill (low priority, fill what's left)
   vision: In1.Cu GND (whole board)       In2.Cu +3V3_ESP (whole board)
           F.Cu GND fill, B.Cu GND fill

   The ESP32-S3 antenna keep-out (part of U2's footprint) stops every pour
   on every layer under the antenna.

3. A 0.3 mm no-tracks border along the board edge (rule areas), because
   Freerouting doesn't apply KiCad's 0.25 mm copper-to-edge rule.

Zones are filled at the end so the autorouter sees the planes.
"""

import json
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGIN = (150.0, 100.0)
HALF_W, HALF_H = 16.0, 15.0
ZONE_TAG = "dronekit_"              # zones this script owns (by name prefix)


def mm(v):
    return pcbnew.FromMM(v)


def cls(name, track, via, drill, clearance=0.1, dp_w=None, dp_gap=None, prio=10):
    return {"name": name, "clearance": clearance, "track_width": track,
            "via_diameter": via, "via_drill": drill,
            "microvia_diameter": 0.3, "microvia_drill": 0.1,
            "diff_pair_width": dp_w or track, "diff_pair_gap": dp_gap or 0.15,
            "diff_pair_via_gap": 0.25, "wire_width": 6, "bus_width": 12, "line_style": 0,
            "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)",
            "priority": prio}


CLASSES = [
    cls("Motor", 0.80, 0.60, 0.30, prio=0),
    cls("Power", 0.40, 0.60, 0.30, prio=1),
    cls("Rail", 0.30, 0.45, 0.20, prio=2),
    cls("USB", 0.20, 0.45, 0.20, dp_w=0.20, dp_gap=0.15, prio=3),
]
PATTERNS = {
    "fc": {
        "Motor": ["/VBAT_RAW", "/M1_NEG", "/M2_NEG", "/M3_NEG", "/M4_NEG"],
        "Power": ["/VBAT", "/+3V8", "/VBUS", "/BB_L1", "/BB_L2", "/GND"],
        "Rail":  ["/+3V3_SYS", "/+3V3_ESP"],
        "USB":   ["/USB_DP", "/USB_DN", "/STM_USB_DP", "/STM_USB_DN",
                  "/ESP_USB_DP", "/ESP_USB_DN"],
    },
    "vision": {
        "Power": ["/+3V8", "/GND"],
        "Rail":  ["/+3V3_ESP", "/+3V3_SYS", "/+2V8_CAM", "/+1V2_CAM"],
        "USB":   ["/ESP_USB_DP", "/ESP_USB_DN"],
    },
}
ZONES = {   # (layer, net, priority)
    "fc":     [("In1.Cu", "/GND", 0), ("In2.Cu", "/+3V3_SYS", 0),
               ("F.Cu", "/GND", 0), ("B.Cu", "/GND", 0)],
    "vision": [("In1.Cu", "/GND", 0), ("In2.Cu", "/+3V3_ESP", 0),
               ("F.Cu", "/GND", 0), ("B.Cu", "/GND", 0)],
}


def write_classes(name):
    path = os.path.join(HERE, f"{name}.kicad_pro")
    pro = json.load(open(path, encoding="utf8"))
    ns = pro.setdefault("net_settings", {})
    default = next((c for c in ns.get("classes", []) if c.get("name") == "Default"), None)
    if default is None:
        raise SystemExit(f"{name}.kicad_pro has no Default net class: run build_pcb.py first")
    default["priority"] = 2147483647
    ns["classes"] = [default] + CLASSES
    ns["netclass_patterns"] = [{"netclass": c, "pattern": n}
                               for c, nets in PATTERNS[name].items() for n in nets]
    ns.setdefault("meta", {"version": 4})
    with open(path, "w", encoding="utf8", newline="\n") as f:
        json.dump(pro, f, indent=2)
        f.write("\n")


def add_zones(board, name):
    # Update this script's zones in place if they exist (removing zones and
    # adding new ones in the same session trips a KiCad 10 SWIG wrapper bug).
    existing = {z.GetZoneName(): z for z in board.Zones() if z.GetZoneName().startswith(ZONE_TAG)}
    wanted = {f"{ZONE_TAG}{layer}_{net.strip('/')}" for layer, net, _ in ZONES[name]}
    for zname, z in existing.items():
        if zname not in wanted:
            board.Remove(z)
    for layer, net, prio in ZONES[name]:
        ni = board.FindNet(net)
        if ni is None:
            raise SystemExit(f"{name}: no net {net}")
        zname = f"{ZONE_TAG}{layer}_{net.strip('/')}"
        z = existing.get(zname)
        new = z is None
        if new:
            z = pcbnew.ZONE(board)
            z.SetZoneName(zname)
        z.SetLayer(board.GetLayerID(layer))
        z.SetNet(ni)
        z.SetAssignedPriority(prio)
        z.SetLocalClearance(mm(0.2))
        z.SetMinThickness(mm(0.15))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL)   # SMD solid, THT thermal
        z.SetThermalReliefGap(mm(0.25))
        z.SetThermalReliefSpokeWidth(mm(0.3))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        if new:
            o = z.Outline()
            o.NewOutline()
            for x, y in ((-HALF_W, -HALF_H), (HALF_W, -HALF_H), (HALF_W, HALF_H), (-HALF_W, HALF_H)):
                o.Append(mm(ORIGIN[0] + x), mm(ORIGIN[1] + y))
            board.Add(z)


EDGE_KEEP = 0.3     # mm: no tracks this close to the board edge (Freerouting
                    # doesn't apply KiCad's 0.25 mm copper-to-edge rule itself)


def add_edge_keepout(board):
    """Four thin rule areas along the board edges: tracks and vias not
    allowed, pads and parts allowed (edge connectors stay legal)."""
    for z in list(board.Zones()):
        if z.GetIsRuleArea() and z.GetZoneName().startswith(ZONE_TAG + "edge"):
            return                                  # already there
    k = EDGE_KEEP
    strips = {"edge_-y": (-HALF_W, -HALF_H, HALF_W, -HALF_H + k),
              "edge_+y": (-HALF_W, HALF_H - k, HALF_W, HALF_H),
              "edge_-x": (-HALF_W, -HALF_H, -HALF_W + k, HALF_H),
              "edge_+x": (HALF_W - k, -HALF_H, HALF_W, HALF_H)}
    ls = pcbnew.LSET()
    for name in ("F.Cu", "In1.Cu", "In2.Cu", "B.Cu"):
        ls.AddLayer(board.GetLayerID(name))
    for tag, (x0, y0, x1, y1) in strips.items():
        z = pcbnew.ZONE(board)
        z.SetIsRuleArea(True)
        z.SetZoneName(ZONE_TAG + tag)
        z.SetLayerSet(ls)
        z.SetDoNotAllowTracks(True)
        z.SetDoNotAllowVias(True)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowFootprints(False)
        z.SetDoNotAllowZoneFills(False)
        o = z.Outline()
        o.NewOutline()
        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            o.Append(mm(ORIGIN[0] + x), mm(ORIGIN[1] + y))
        board.Add(z)


PLANE_NETS = {"/GND", "/+3V3_SYS"}


def solid_b2b_gnd(board):
    """The B2B connector's GND and +3V3_SYS pins join their pours solid, not
    with thermal spokes (and so do the USB-C shell pins): on the 1.27 mm grid its neighbours' tracks leave too
    little room for the spokes (DRC 'starved thermal'). Small pins: still solders."""
    for fp in board.GetFootprints():
        if fp.GetReference() in ("J200", "J201", "J90"):      # J90: the USB-C shell pins
            for p in fp.Pads():
                if p.GetNetname() in PLANE_NETS and p.HasHole():
                    p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else ""
    if name not in ("fc", "vision"):
        raise SystemExit("usage: route_setup.py fc|vision")
    write_classes(name)
    pcb = os.path.join(HERE, f"{name}.kicad_pcb")
    board = pcbnew.LoadBoard(pcb)       # reads the classes just written
    add_zones(board, name)
    add_edge_keepout(board)
    solid_b2b_gnd(board)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(pcb)
    print(f">>> {name}: {len(CLASSES)} net classes + Default, "
          f"{len(ZONES[name])} zones ({', '.join(l + ' ' + n for l, n, _ in ZONES[name])})")


if __name__ == "__main__":
    main()
