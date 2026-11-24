"""
DroneKit Pro - widen the high-current paths with copper pours.

Run with KiCad's own Python, after handroute.py:

    "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" power_pour.py fc

On a 1S brushed whoop the motors run straight off the battery: about 2.5 A
per motor at full throttle, about 10 A through VBAT_RAW from the battery
pads to the four motors. The routers lay these nets as 0.8 mm tracks
(net class "Motor"), good for about 2.7 A on an outer layer and about 1 A
on an inner one (JLCPCB 4-layer: 1 oz outer, 0.5 oz inner). This script:

1. Puts a copper pour of the net along every track it has on F.Cu or B.Cu,
   on that layer: a corridor CORRIDOR[net] mm either side of the track's centre
   line, merged with the net's pads. The pour outranks the GND and +3V3
   pours, connects to its pads solid, and like any pour it stops short of
   other nets' copper, so it is as wide as the free space allows.
2. Adds vias of the net (0.6 / 0.3 mm) around every via it already has, up
   to EXTRA_VIAS more each, wherever the new via sits fully inside the
   net's pour on the layers that via joins and clears every other net, so a
   layer change no longer squeezes the whole current through one via.
3. Refills the zones, saves, and prints, for every track of these nets,
   the narrowest copper width found along it and what that carries
   (IPC-2221, 20 degC rise).

Re-running is safe: the pours it made before (named POUR_TAG...) are
removed and made again; the extra vias are only added on the first run.
"""

import math
import os
import sys

import pcbnew

import fanout                       # clearance helpers: Copper, inside, keepout

HERE = os.path.dirname(os.path.abspath(__file__))
POUR_TAG = "dronekit_power_"
CORRIDOR = {"/VBAT_RAW": 1.5,       # mm either side of the track centre line
            "/M1_NEG": 1.0, "/M2_NEG": 1.0, "/M3_NEG": 1.0, "/M4_NEG": 1.0}
# the most any part of the net carries: 4 motors on VBAT_RAW at the battery
# pads, less on each branch (2 motors per side, 1 per motor stub)
AMPS = {"/VBAT_RAW": 10.0, "/M1_NEG": 2.5, "/M2_NEG": 2.5, "/M3_NEG": 2.5, "/M4_NEG": 2.5}
PRIORITY = 5                        # above the GND / +3V3 pours (0)
VIA_D, VIA_DRILL = 0.6, 0.3         # the Power class via
EXTRA_VIAS = 6
LAYERS = (pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu)
# pours go on the outer layers only: In2 is the 3.3 V plane, 0.5 oz, and
# the power nets only cross it in vias (preroute_power.py prices it out); the
# one VBAT_RAW track there is the battery-sense line to R15, which carries
# no current
POUR_LAYERS = (pcbnew.F_Cu, pcbnew.B_Cu)
OZ = {pcbnew.F_Cu: 1.0, pcbnew.B_Cu: 1.0, pcbnew.In2_Cu: 0.5}   # JLCPCB 4-layer default


def mm(v):
    return pcbnew.FromMM(v)


def to_mm(v):
    return pcbnew.ToMM(v)


def ipc_amps(width_mm, layer, rise=20.0):
    """IPC-2221 current for a track of this width on this layer."""
    area_mil2 = (width_mm / 0.0254) * (1.378 * OZ[layer])
    k = 0.048 if layer in (pcbnew.F_Cu, pcbnew.B_Cu) else 0.024
    return k * rise ** 0.44 * area_mil2 ** 0.725


def corridor(board, code, layer, half):
    """Union of the net's tracks on this layer, each widened to 2 * half,
    and its pads there, a little enlarged."""
    poly = pcbnew.SHAPE_POLY_SET()
    err = mm(0.005)
    for t in board.GetTracks():
        if t.GetNetCode() != code or t.GetClass() == "PCB_VIA" or t.GetLayer() != layer:
            continue
        grow = max(0, mm(half) - t.GetWidth() // 2)
        t.TransformShapeToPolygon(poly, layer, grow, err, pcbnew.ERROR_INSIDE)
    if poly.OutlineCount() == 0:
        return poly
    for p in board.GetPads():
        if p.GetNetCode() == code and p.IsOnLayer(layer):
            p.TransformShapeToPolygon(poly, layer, mm(0.3), err, pcbnew.ERROR_INSIDE)
    poly.Simplify()
    return poly


def add_pours(board):
    made = 0
    for net, half in CORRIDOR.items():
        ni = board.FindNet(net)
        for layer in POUR_LAYERS:
            poly = corridor(board, ni.GetNetCode(), layer, half)
            for k in range(poly.OutlineCount()):
                z = pcbnew.ZONE(board)
                z.SetZoneName(f"{POUR_TAG}{net.strip('/')}_{board.GetLayerName(layer)}_{k}")
                z.SetLayer(layer)
                z.SetNet(ni)
                z.SetAssignedPriority(PRIORITY)
                z.SetLocalClearance(mm(0.2))
                z.SetMinThickness(mm(0.2))
                z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
                z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
                o = z.Outline()
                o.NewOutline()
                chain = poly.COutline(k)
                for i in range(chain.PointCount()):
                    pt = chain.CPoint(i)
                    o.Append(pt.x, pt.y)
                board.Add(z)
                made += 1
    return made


def filled(board, code, layer):
    """The net's copper on this layer after the fill: its pours' fill."""
    out = []
    for z in board.Zones():
        if z.GetNetCode() == code and z.GetLayer() == layer and not z.GetIsRuleArea():
            out.append(z.GetFilledPolysList(layer))
    return out


def in_fill(fills, x, y, r):
    """The whole circle of radius r at (x, y) lies in one of the fills."""
    pts = [(x, y)] + [(x + r * math.cos(a), y + r * math.sin(a))
                      for a in [i * math.pi / 4 for i in range(8)]]
    for f in fills:
        if all(f.Contains(pcbnew.VECTOR2I(int(px), int(py))) for px, py in pts):
            return True
    return False


def via_layers(board, via):
    """The layers the net's tracks join this via on."""
    out = set()
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA" or t.GetNetCode() != via.GetNetCode():
            continue
        for e in (t.GetStart(), t.GetEnd()):
            if (e - via.GetPosition()).EuclideanNorm() < mm(0.05):
                out.add(t.GetLayer())
    return out


def add_via_clusters(board):
    cu = fanout.Copper(board)
    added = 0
    for net in CORRIDOR:
        ni = board.FindNet(net)
        code = ni.GetNetCode()
        fills = {l: filled(board, code, l) for l in LAYERS}
        for v in [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA" and t.GetNetCode() == code]:
            joins = via_layers(board, v) or {pcbnew.F_Cu, pcbnew.B_Cu}
            cx, cy = v.GetPosition().x, v.GetPosition().y
            n_here = 0
            for ring in [0.7 + 0.1 * i for i in range(12)]:
                steps = max(8, int(2 * math.pi * ring / 0.2))
                for s in range(steps):
                    if n_here >= EXTRA_VIAS:
                        break
                    a = 2 * math.pi * s / steps
                    x, y = cx + mm(ring) * math.cos(a), cy + mm(ring) * math.sin(a)
                    r = mm(VIA_D) // 2
                    if not fanout.inside(x, y) or fanout.keepout(board, x, y):
                        continue
                    if not all(in_fill(fills[l], x, y, r) for l in joins):
                        continue
                    shape = pcbnew.SHAPE_CIRCLE(pcbnew.VECTOR2I(int(x), int(y)), r)
                    if not cu.clear(shape, fanout.VIA_LAYERS, code):
                        continue
                    if not cu.hole_clear(x, y, mm(VIA_DRILL) // 2):
                        continue
                    nv = pcbnew.PCB_VIA(board)
                    nv.SetPosition(pcbnew.VECTOR2I(int(x), int(y)))
                    nv.SetWidth(mm(VIA_D))
                    nv.SetDrill(mm(VIA_DRILL))
                    nv.SetNet(ni)
                    board.Add(nv)
                    for l in (pcbnew.F_Cu, pcbnew.B_Cu):
                        cu.items.append((code, l, nv.GetEffectiveShape(l)))
                    cu.holes.append((int(x), int(y), mm(VIA_DRILL) // 2))
                    n_here += 1
                    added += 1
    return added


def narrowest(board):
    """For every track of these nets: the narrowest width of the net's copper
    (pour fill) across it, measured every 0.25 mm along it, away from its ends."""
    rows = []
    for net in CORRIDOR:
        code = board.FindNet(net).GetNetCode()
        for layer in POUR_LAYERS:
            fills = filled(board, code, layer)
            if not fills:
                continue
            worst = None
            for t in board.GetTracks():
                if t.GetNetCode() != code or t.GetClass() == "PCB_VIA" or t.GetLayer() != layer:
                    continue
                ax, ay, bx, by = t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y
                length = math.hypot(bx - ax, by - ay)
                if length < mm(1.4):
                    continue
                ux, uy = (bx - ax) / length, (by - ay) / length
                nx, ny = -uy, ux
                d = mm(0.6)
                while d <= length - mm(0.6):
                    px, py = ax + ux * d, ay + uy * d
                    w = 0
                    for sgn in (1, -1):
                        e = 0
                        while e < mm(5) and any(f.Contains(pcbnew.VECTOR2I(int(px + sgn * nx * (e + mm(0.025))),
                                                                           int(py + sgn * ny * (e + mm(0.025)))))
                                                for f in fills):
                            e += mm(0.025)
                        w += e
                    if worst is None or w < worst[0]:
                        worst = (w, px, py)
                    d += mm(0.25)
            if worst:
                rows.append((net, layer, to_mm(worst[0]), worst[1], worst[2]))
    return rows


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else ""
    if name != "fc":
        raise SystemExit("usage: power_pour.py fc   (vision carries no motor current)")
    pcb = os.path.join(HERE, f"{name}.kicad_pcb")
    board = pcbnew.LoadBoard(pcb)
    old = [z for z in board.Zones() if z.GetZoneName().startswith(POUR_TAG)]
    for z in old:
        board.Remove(z)
    filler = pcbnew.ZONE_FILLER(board)
    made = add_pours(board)
    filler.Fill(board.Zones())
    vias = add_via_clusters(board) if not old else 0
    filler.Fill(board.Zones())
    board.Save(pcb)
    print(f">>> {name}: {made} power pours"
          + (f", {vias} extra vias" if not old else " (pours remade; vias kept from the first run)"))
    bb = board.GetBoardEdgesBoundingBox()
    cx, cy = bb.Centre().x, bb.Centre().y
    for net, layer, w, x, y in narrowest(board):
        print(f"    {net:10s} {board.GetLayerName(layer):6s} narrowest {w:4.2f} mm "
              f"at ({to_mm(x - cx):6.2f}, {to_mm(y - cy):6.2f}): "
              f"{ipc_amps(w, layer):4.1f} A at 20 degC rise (the net carries up to {AMPS[net]:.1f} A in all)")


if __name__ == "__main__":
    main()
