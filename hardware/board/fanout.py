"""
DroneKit Pro - fan plane nets out to their inner planes, and stitch ground.

Run with KiCad's own Python, after autoroute.py:

    "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" fanout.py fc

1. Fan-out: every SMD pad of a plane net (GND -> In1.Cu, the board's 3.3 V
   rail -> In2.Cu) that has no copper path to its plane gets a short track
   and a 0.45/0.2 mm via down to it. The via goes at the first spot, walking
   outward from the pad, where the via and the track clear every other
   net's copper (pads, tracks, vias, holes) by CLEAR.
2. Stitching: GND vias on a STITCH_PITCH grid wherever F.Cu and B.Cu are
   free of other nets, then one GND via inside every top/bottom ground-fill
   island that still has none, so no island floats and every ground pad
   on an island reaches In1.Cu.

Then the zones are refilled and the board saved. Existing copper is never
moved. Pads it can't fan out are listed.
"""

import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGIN = (150.0, 100.0)
HALF_W, HALF_H, EDGE = 16.0, 15.0, 0.6     # vias at least EDGE mm inside the outline
VIA_D, VIA_DRILL = 0.45, 0.2
CLEAR = 0.15                               # mm, copper to other-net copper
HOLE_CLEAR = 0.3                           # mm, drill edge to drill edge
STITCH_PITCH = 2.0
VIA_LAYERS = (pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu)   # In1 is the GND plane
PLANES = {"fc": {"/GND": "In1.Cu", "/+3V3_SYS": "In2.Cu"},
          "vision": {"/GND": "In1.Cu", "/+3V3_ESP": "In2.Cu"}}


def mm(v):
    return pcbnew.FromMM(v)


def to_mm(v):
    return pcbnew.ToMM(v)


class Copper:
    """Other-net copper on the outer layers and on In2.Cu (signal tracks the
    router put there), for clearance checks. A via passes every layer."""

    def __init__(self, board):
        self.b = board
        self.items = []          # (netcode, layer, shape)
        self.holes = []          # (x, y, r) in nm
        self.refresh()

    def refresh(self):
        b = self.b
        self.items, self.holes = [], []
        for p in b.GetPads():
            for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
                if p.IsOnLayer(layer):
                    self.items.append((p.GetNetCode(), layer, p.GetEffectiveShape(layer)))
            if p.HasHole():
                d = max(p.GetDrillSize().x, p.GetDrillSize().y)
                self.holes.append((p.GetPosition().x, p.GetPosition().y, d // 2))
        for t in b.GetTracks():
            if t.GetClass() == "PCB_VIA":
                for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
                    self.items.append((t.GetNetCode(), layer, t.GetEffectiveShape(layer)))
                self.holes.append((t.GetPosition().x, t.GetPosition().y, t.GetDrillValue() // 2))
            elif t.GetLayer() in (pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In2_Cu):
                self.items.append((t.GetNetCode(), t.GetLayer(), t.GetEffectiveShape(t.GetLayer())))

    def clear(self, shape, layers, net, extra_holes=None):
        c = mm(CLEAR)
        for n, layer, s in self.items:
            if n != net and layer in layers and s.Collide(shape, c):
                return False
        return True

    def hole_clear(self, x, y, r):
        for hx, hy, hr in self.holes:
            if math.hypot(hx - x, hy - y) < r + hr + mm(HOLE_CLEAR):
                return False
        return True


CORNER_R = 2.0                              # mm, board corner radius (build_pcb.py)


def inside(x, y):
    ax, ay = abs(to_mm(x) - ORIGIN[0]), abs(to_mm(y) - ORIGIN[1])
    if ax > HALF_W - EDGE or ay > HALF_H - EDGE:
        return False
    # the rounded corners: stay EDGE inside the arc, not just the square
    cx, cy = HALF_W - CORNER_R, HALF_H - CORNER_R
    if ax > cx and ay > cy and math.hypot(ax - cx, ay - cy) > CORNER_R - EDGE:
        return False
    return not (abs(ax - 12.75) < 2.2 and abs(ay - 12.75) < 2.2)     # mounting holes


def keepout(board, x, y):
    """Inside any rule area (the ESP32-S3 antenna keep-out)."""
    pt = pcbnew.VECTOR2I(int(x), int(y))
    for z in board.Zones():
        if z.GetIsRuleArea() and z.Outline().Contains(pt):
            return True
    for fp in board.GetFootprints():
        for z in fp.Zones():
            if z.GetIsRuleArea() and z.Outline().Contains(pt):
                return True
    return False


def reaches_plane(board, conn, pad, plane_layer):
    seen = {pad.m_Uuid.AsString()}
    stack = [pad]
    while stack:
        it = stack.pop()
        for o in conn.GetConnectedItems(it):
            k = o.m_Uuid.AsString()
            if k in seen:
                continue
            seen.add(k)
            if o.GetClass() == "ZONE" and o.GetLayer() == plane_layer:
                return True
            if o.GetClass() == "PCB_VIA" or (o.GetClass() == "PAD" and o.HasHole()):
                return True                      # through copper reaches every layer
            stack.append(o)
    return False


def add_via(board, x, y, net):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(int(x), int(y)))
    v.SetWidth(mm(VIA_D))
    v.SetDrill(mm(VIA_DRILL))
    v.SetNet(net)
    board.Add(v)
    return v


def add_track(board, a, b, layer, width, net):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(a)
    t.SetEnd(b)
    t.SetLayer(layer)
    t.SetWidth(width)
    t.SetNet(net)
    board.Add(t)
    return t


def fanout_pad(board, cu, pad, net):
    layer = pcbnew.F_Cu if pad.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu
    px, py = pad.GetPosition().x, pad.GetPosition().y
    width = min(mm(0.3), min(pad.GetSize().x, pad.GetSize().y))
    r_via = mm(VIA_D) // 2
    for ring in [x * 0.25 for x in range(2, 13)]:            # 0.5 .. 3.0 mm
        n = max(8, int(2 * math.pi * ring / 0.25))
        for k in range(n):
            a = 2 * math.pi * k / n
            x, y = px + mm(ring * math.cos(a)), py + mm(ring * math.sin(a))
            if not inside(x, y) or keepout(board, x, y):
                continue
            c = pcbnew.SHAPE_CIRCLE(pcbnew.VECTOR2I(int(x), int(y)), r_via)
            if not cu.clear(c, (pcbnew.F_Cu, pcbnew.B_Cu), net.GetNetCode()):
                continue
            if not cu.hole_clear(x, y, mm(VIA_DRILL) // 2):
                continue
            seg = pcbnew.SHAPE_SEGMENT(pcbnew.VECTOR2I(px, py), pcbnew.VECTOR2I(int(x), int(y)), width)
            if not cu.clear(seg, (layer,), net.GetNetCode()):
                continue
            v = add_via(board, x, y, net)
            t = add_track(board, pcbnew.VECTOR2I(px, py), pcbnew.VECTOR2I(int(x), int(y)), layer, width, net)
            cu.items.append((net.GetNetCode(), pcbnew.F_Cu, v.GetEffectiveShape(pcbnew.F_Cu)))
            cu.items.append((net.GetNetCode(), pcbnew.B_Cu, v.GetEffectiveShape(pcbnew.B_Cu)))
            cu.items.append((net.GetNetCode(), layer, t.GetEffectiveShape(layer)))
            cu.holes.append((int(x), int(y), mm(VIA_DRILL) // 2))
            return True
    return False


def stitch(board, cu, gnd):
    added = 0
    r_via = mm(VIA_D) // 2
    steps_x = int(2 * (HALF_W - EDGE) / STITCH_PITCH)
    steps_y = int(2 * (HALF_H - EDGE) / STITCH_PITCH)
    for i in range(steps_x + 1):
        for j in range(steps_y + 1):
            x = mm(ORIGIN[0] - (HALF_W - EDGE) + i * STITCH_PITCH)
            y = mm(ORIGIN[1] - (HALF_H - EDGE) + j * STITCH_PITCH)
            if not inside(x, y) or keepout(board, x, y):
                continue
            c = pcbnew.SHAPE_CIRCLE(pcbnew.VECTOR2I(int(x), int(y)), r_via + mm(0.1))
            if not cu.clear(c, (pcbnew.F_Cu, pcbnew.B_Cu), -1) \
                    or not cu.clear(c, VIA_LAYERS, gnd.GetNetCode()):   # clear of all outer copper, other nets on In2
                continue
            if not cu.hole_clear(x, y, mm(VIA_DRILL) // 2):
                continue
            v = add_via(board, x, y, gnd)
            for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
                cu.items.append((gnd.GetNetCode(), layer, v.GetEffectiveShape(layer)))
            cu.holes.append((int(x), int(y), mm(VIA_DRILL) // 2))
            added += 1
    return added


def stitch_islands(board, cu, gnd):
    """A GND via in every top/bottom ground-fill island that has none, so no
    island floats: the via's centre sits in the island's copper and the via
    is clear of other nets on every layer it passes (the fill then flows
    round it and joins it solidly)."""
    r_via = mm(VIA_D) // 2
    margin = mm(0.05)
    gnd_through = [(t.GetPosition()) for t in board.GetTracks()
                   if t.GetClass() == "PCB_VIA" and t.GetNetCode() == gnd.GetNetCode()]
    gnd_through += [p.GetPosition() for p in board.GetPads()
                    if p.HasHole() and p.GetNetCode() == gnd.GetNetCode()]
    added, stranded = 0, 0
    for z in board.Zones():
        if z.GetNetCode() != gnd.GetNetCode() or z.GetLayer() not in (pcbnew.F_Cu, pcbnew.B_Cu):
            continue
        layer = z.GetLayer()
        other = pcbnew.B_Cu if layer == pcbnew.F_Cu else pcbnew.F_Cu
        polys = z.GetFilledPolysList(layer)
        for i in range(polys.OutlineCount()):
            outline = polys.Outline(i)
            holes = [polys.CHole(i, h) for h in range(polys.HoleCount(i))]

            def in_copper(pt):
                return outline.PointInside(pt) and not any(h.PointInside(pt) for h in holes)

            if any(in_copper(pt) for pt in gnd_through):
                continue
            bb = outline.BBox()
            placed = False
            step = mm(0.05)
            y = bb.GetTop() + margin
            while y <= bb.GetBottom() - margin and not placed:
                x = bb.GetLeft() + margin
                while x <= bb.GetRight() - margin and not placed:
                    pt = pcbnew.VECTOR2I(int(x), int(y))
                    # (no Distance() test: it is 0 for any point inside a
                    # closed outline; clear() below keeps other nets away)
                    if (in_copper(pt) and inside(x, y) and not keepout(board, x, y)):
                        c = pcbnew.SHAPE_CIRCLE(pt, r_via)
                        if cu.clear(c, VIA_LAYERS, gnd.GetNetCode()) and cu.hole_clear(x, y, mm(VIA_DRILL) // 2):
                            v = add_via(board, x, y, gnd)
                            for l in (pcbnew.F_Cu, pcbnew.B_Cu):
                                cu.items.append((gnd.GetNetCode(), l, v.GetEffectiveShape(l)))
                            cu.holes.append((int(x), int(y), mm(VIA_DRILL) // 2))
                            gnd_through.append(pt)
                            added += 1
                            placed = True
                    x += step
                y += step
            if not placed:
                stranded += 1
    return added, stranded


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else ""
    if name not in PLANES:
        raise SystemExit("usage: fanout.py fc|vision")
    pcb = os.path.join(HERE, f"{name}.kicad_pcb")
    board = pcbnew.LoadBoard(pcb)
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    board.BuildConnectivity()
    conn = board.GetConnectivity()
    cu = Copper(board)

    done, failed = 0, []
    for net_name, plane in PLANES[name].items():
        net = board.FindNet(net_name)
        plane_layer = board.GetLayerID(plane)
        for pad in list(board.GetPads()):
            if pad.GetNetname() != net_name or pad.HasHole():
                continue
            if reaches_plane(board, conn, pad, plane_layer):
                continue
            if fanout_pad(board, cu, pad, net):
                done += 1
            else:
                failed.append(f"{pad.GetParentFootprint().GetReference()}.{pad.GetNumber()} ({net_name})")
    gnd = board.FindNet("/GND")
    stitched = stitch(board, cu, gnd)
    filler.Fill(board.Zones())
    islands, stranded = stitch_islands(board, cu, gnd)
    filler.Fill(board.Zones())
    board.Save(pcb)
    print(f">>> {name}: fanned out {done} plane pads, added {stitched} GND grid vias "
          f"and {islands} island vias ({stranded} islands too small for a via)")
    if failed:
        print(">>> no room to fan out: " + ", ".join(failed))


if __name__ == "__main__":
    main()
