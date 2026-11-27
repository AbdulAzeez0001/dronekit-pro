"""
DroneKit Pro - finish the connections the autorouter left (a small maze router).

Run with KiCad's own Python, after autoroute.py and fanout.py:

    "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" handroute.py fc

1. Asks KiCad's DRC (JSON) for the unconnected pairs.
2. Builds a clearance map of all existing copper on F.Cu, In2.Cu and B.Cu
   on a 0.05 mm grid: for every cell, the distance to the nearest copper and
   its net, and the distance to the nearest copper of any *other* net (so one
   map serves every net), plus the distance to the nearest hole and to the
   board edge.
3. For each pair (shortest first), an A* search on that grid from one item's
   copper to the other's: 45-degree moves on F.Cu / In2.Cu / B.Cu, 0.45/0.2
   vias between them where a via fits. The net-class track width is tried
   first, then narrower (down to 0.12 mm) if there's no path. In1.Cu (the
   GND plane) is never routed.
4. GND: every top/bottom ground-fill island with no via to In1.Cu gets a
   short track out to the nearest spot a via fits, and the via.
5. Adds the tracks and vias, refills the zones and saves.

Rip-up: a pair with no free path is searched again through other nets'
tracks and vias, at a cost (RIP_COST per grid step). The wires it crosses,
each back to the nearest pad, branch or dead end, are removed and get
routed in the next round. Pads, holes and the PROTECTED nets (battery,
motors, supply rails, USB-in) are never ripped up.

Rounds: steps 1-5 are one round, and each round runs in a fresh process
(KiCad 10's SWIG wrapper degrades after many edits in one session). Up to
ROUNDS rounds. Every round's board is saved in .routing/ as
<board>_handroute_roundN.kicad_pcb, and the best one is copied back at the
end. Best means: fewest shorts and clearance errors, then the fewest open
connections plus thermal-relief errors.

Clearances: 0.13 mm to other nets (board rule 0.10 + grid margin), 0.25 mm
hole to hole (+ margin), tracks and vias kept out of the 0.3 mm edge strip.
Run kicad-cli DRC afterwards: this script doesn't check against zone fills
of other nets (they reflow around new copper) and can strand new ground
islands, which fanout.py then stitches.
"""

import heapq
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from array import array

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
ORIGIN = (150.0, 100.0)
HALF_W, HALF_H = 16.0, 15.0
G = 0.05                                    # grid, mm
X0, Y0 = ORIGIN[0] - HALF_W, ORIGIN[1] - HALF_H
NX, NY = int(round(2 * HALF_W / G)) + 1, int(round(2 * HALF_H / G)) + 1
N = NX * NY
LAYERS = [pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
LAYER_COST = [1.0, 1.3, 1.0]                # In2 is the 3.3 V plane: use it last
CLR = 0.13                                  # mm, other-net copper
EDGE_KEEP = 0.3 + 0.02                      # the edge rule-area strip
VIA_D, VIA_DRILL = 0.45, 0.2
H2H = 0.25 + 0.03                           # hole to hole
VIA_COST = 30                               # grid steps (1.5 mm)
R = 0.62                                    # map radius around each item, mm
BIG = 9.0
MAX_EXPAND = 900000
WIDTHS = (0.8, 0.4, 0.3, 0.2, 0.15, 0.12)
TRACKS = []                                 # the board's tracks and vias (see one_round)
RIP_COST = 60                              # per grid step through rippable copper
ROUNDS = 12
# nets whose copper is never ripped up (battery, motor, supply and USB-in paths)
PROTECTED = {"/VBAT_RAW", "/M1_NEG", "/M2_NEG", "/M3_NEG", "/M4_NEG", "/VBAT", "/+3V8",
             "/VBUS", "/BB_L1", "/BB_L2"}
SQ2 = math.sqrt(2)
MOVES = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
         (1, 1, SQ2), (1, -1, SQ2), (-1, 1, SQ2), (-1, -1, SQ2)]


def mm(v):
    return pcbnew.FromMM(v)


def to_mm(v):
    return pcbnew.ToMM(v)


# --------------------------------------------------------------------------
# geometry (mm, pure Python)
# --------------------------------------------------------------------------
def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def poly_dist(px, py, pts):
    """Signed distance to a closed polygon: negative inside."""
    inside = False
    best = BIG
    n = len(pts)
    for k in range(n):
        ax, ay = pts[k]
        bx, by = pts[(k + 1) % n]
        if (ay > py) != (by > py) and px < ax + (py - ay) * (bx - ax) / (by - ay):
            inside = not inside
        d = seg_dist(px, py, ax, ay, bx, by)
        if d < best:
            best = d
    return -best if inside else best


def chain_pts(chain):
    return [(to_mm(chain.CPoint(k).x), to_mm(chain.CPoint(k).y)) for k in range(chain.PointCount())]


def cell(x, y):
    ix, iy = int(round((x - X0) / G)), int(round((y - Y0) / G))
    if 0 <= ix < NX and 0 <= iy < NY:
        return iy * NX + ix
    return None


def cell_xy(i):
    return X0 + (i % NX) * G, Y0 + (i // NX) * G


def cells_in(xmin, ymin, xmax, ymax):
    i0, i1 = max(0, int((xmin - X0) / G)), min(NX - 1, int((xmax - X0) / G) + 1)
    j0, j1 = max(0, int((ymin - Y0) / G)), min(NY - 1, int((ymax - Y0) / G) + 1)
    for j in range(j0, j1 + 1):
        y = Y0 + j * G
        for i in range(i0, i1 + 1):
            yield j * NX + i, X0 + i * G, y


# --------------------------------------------------------------------------
# copper shapes of board items: (layers, bbox, signed distance function)
# --------------------------------------------------------------------------
def pad_shapes(p):
    out = []
    pth = p.HasHole() and p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH
    for li, L in enumerate(LAYERS):
        if not (p.IsOnLayer(L) or (pth and L == pcbnew.In2_Cu)):
            continue
        src = L if p.IsOnLayer(L) else pcbnew.F_Cu
        ps = p.GetEffectivePolygon(src, pcbnew.ERROR_INSIDE)
        polys = [chain_pts(ps.COutline(k)) for k in range(ps.OutlineCount())]
        polys = [q for q in polys if len(q) >= 3]
        if not polys:
            continue
        xs = [x for q in polys for x, _ in q]
        ys = [y for q in polys for _, y in q]

        def f(x, y, polys=polys):
            return min(poly_dist(x, y, q) for q in polys)
        out.append(([li], (min(xs), min(ys), max(xs), max(ys)), f))
    return out


def track_shape(ax, ay, bx, by, w):
    hw = w / 2
    return ((min(ax, bx) - hw, min(ay, by) - hw, max(ax, bx) + hw, max(ay, by) + hw),
            lambda x, y: seg_dist(x, y, ax, ay, bx, by) - hw)


def circle_shape(cx, cy, r):
    return ((cx - r, cy - r, cx + r, cy + r), lambda x, y: math.hypot(x - cx, y - cy) - r)


# --------------------------------------------------------------------------
# clearance map
# --------------------------------------------------------------------------
class Field:
    def __init__(self):
        self.d1 = [array("f", [BIG]) * N for _ in LAYERS]
        self.n1 = [array("i", [-2]) * N for _ in LAYERS]
        self.d2 = [array("f", [BIG]) * N for _ in LAYERS]
        self.p1 = [array("f", [BIG]) * N for _ in LAYERS]     # fixed copper only:
        self.q1 = [array("i", [-2]) * N for _ in LAYERS]      # pads, holes and the
        self.p2 = [array("f", [BIG]) * N for _ in LAYERS]     # protected nets
        self.H = array("f", [BIG]) * N        # to nearest hole edge
        self.Hp = array("f", [BIG]) * N       # to nearest fixed hole edge
        self.E = array("f", [BIG]) * N        # to board edge (inside +)

    @staticmethod
    def _put(d1, n1, d2, i, d, net):
        if n1[i] == net:
            if d < d1[i]:
                d1[i] = d
        elif d < d1[i]:
            d2[i] = d1[i]       # old nearest is another net and was the global min
            d1[i] = d
            n1[i] = net
        elif d < d2[i]:
            d2[i] = d

    def add(self, layers, net, bbox, f, fixed=False):
        x0, y0, x1, y1 = bbox
        for i, x, y in cells_in(x0 - R, y0 - R, x1 + R, y1 + R):
            d = f(x, y)
            if d >= R:
                continue
            for li in layers:
                self._put(self.d1[li], self.n1[li], self.d2[li], i, d, net)
                if fixed:
                    self._put(self.p1[li], self.q1[li], self.p2[li], i, d, net)

    def add_hole(self, cx, cy, r, fixed=False):
        for i, x, y in cells_in(cx - r - R, cy - r - R, cx + r + R, cy + r + R):
            d = math.hypot(x - cx, y - cy) - r
            if d < self.H[i]:
                self.H[i] = d
            if fixed and d < self.Hp[i]:
                self.Hp[i] = d

    def other(self, li, i, net):
        return self.d1[li][i] if self.n1[li][i] != net else self.d2[li][i]

    def other_fixed(self, li, i, net):
        return self.p1[li][i] if self.q1[li][i] != net else self.p2[li][i]

    def track_ok(self, li, i, net, hw):
        return self.E[i] >= EDGE_KEEP + hw and self.other(li, i, net) >= hw + CLR

    def track_fixed_ok(self, li, i, net, hw):
        return self.E[i] >= EDGE_KEEP + hw and self.other_fixed(li, i, net) >= hw + CLR

    def via_ok(self, i, net):
        r = VIA_D / 2
        if self.E[i] < EDGE_KEEP + r or self.H[i] < VIA_DRILL / 2 + H2H:
            return False
        return all(self.other(li, i, net) >= r + CLR for li in range(len(LAYERS)))

    def via_fixed_ok(self, i, net):
        r = VIA_D / 2
        if self.E[i] < EDGE_KEEP + r or self.Hp[i] < VIA_DRILL / 2 + H2H:
            return False
        return all(self.other_fixed(li, i, net) >= r + CLR for li in range(len(LAYERS)))

    def add_track(self, net, li, ax, ay, bx, by, w, fixed=False):
        bbox, f = track_shape(ax, ay, bx, by, w)
        self.add([li], net, bbox, f, fixed)

    def add_via(self, net, x, y, fixed=False, d=VIA_D, drill=VIA_DRILL):
        bbox, f = circle_shape(x, y, d / 2)
        self.add(list(range(len(LAYERS))), net, bbox, f, fixed)
        self.add_hole(x, y, drill / 2, fixed)


def build_field(board):
    F = Field()
    for p in board.GetPads():
        net = p.GetNetCode()
        for layers, bbox, f in pad_shapes(p):
            F.add(layers, net, bbox, f, fixed=True)
        if p.HasHole():
            x, y = to_mm(p.GetPosition().x), to_mm(p.GetPosition().y)
            r = to_mm(max(p.GetDrillSize().x, p.GetDrillSize().y)) / 2
            F.add_hole(x, y, r, fixed=True)
            if p.GetAttribute() != pcbnew.PAD_ATTRIB_PTH:
                # bare (NPTH) hole: hole-to-copper 0.2 mm on every layer
                bbox, f = circle_shape(x, y, r + 0.08)
                F.add(list(range(len(LAYERS))), -1, bbox, f, fixed=True)
    for t in board.GetTracks():
        net = t.GetNetCode()
        fixed = t.GetNetname() in PROTECTED
        if t.GetClass() == "PCB_VIA":
            F.add_via(net, to_mm(t.GetPosition().x), to_mm(t.GetPosition().y), fixed,
                      to_mm(t.GetWidth(pcbnew.F_Cu)), to_mm(t.GetDrillValue()))
            continue
        if t.GetLayer() not in LAYERS:
            continue
        s, e = t.GetStart(), t.GetEnd()
        F.add_track(net, LAYERS.index(t.GetLayer()), to_mm(s.x), to_mm(s.y),
                    to_mm(e.x), to_mm(e.y), to_mm(t.GetWidth()), fixed)
    # board edge
    ps = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(ps, False)
    edge = chain_pts(ps.COutline(0))
    band = 2.0
    for i in range(N):
        x, y = cell_xy(i)
        if (x - X0 < band or X0 + 2 * HALF_W - x < band
                or y - Y0 < band or Y0 + 2 * HALF_H - y < band):
            F.E[i] = -poly_dist(x, y, edge)
    # other keep-out rule areas (not this project's edge strips)
    for z in list(board.Zones()) + [z for fp in board.GetFootprints() for z in fp.Zones()]:
        if not z.GetIsRuleArea() or z.GetZoneName().startswith("dronekit_edge") \
                or not z.GetDoNotAllowTracks():
            continue
        bb = z.GetBoundingBox()
        for i, x, y in cells_in(to_mm(bb.GetLeft()) - 0.6, to_mm(bb.GetTop()) - 0.6,
                                to_mm(bb.GetRight()) + 0.6, to_mm(bb.GetBottom()) + 0.6):
            if z.Outline().Collide(pcbnew.VECTOR2I(mm(x), mm(y)), mm(0.5)):
                F.E[i] = -1.0
    return F


# --------------------------------------------------------------------------
# start / goal cell sets
# --------------------------------------------------------------------------
def item_cells(board, item):
    """{(li, i)} for cells whose centre lies inside the item's copper."""
    out = set()
    cls = item.GetClass()
    if cls == "PAD":
        for layers, bbox, f in pad_shapes(item):
            for i, x, y in cells_in(*bbox):
                if f(x, y) <= -0.02:
                    out.update((li, i) for li in layers)
    elif cls == "PCB_VIA":
        x, y = to_mm(item.GetPosition().x), to_mm(item.GetPosition().y)
        bbox, f = circle_shape(x, y, VIA_D / 2)
        for i, cx, cy in cells_in(*bbox):
            if f(cx, cy) <= -0.02:
                out.update((li, i) for li in range(len(LAYERS)))
    elif cls in ("PCB_TRACK", "PCB_ARC"):
        if item.GetLayer() in LAYERS:
            s, e = item.GetStart(), item.GetEnd()
            bbox, f = track_shape(to_mm(s.x), to_mm(s.y), to_mm(e.x), to_mm(e.y),
                                  to_mm(item.GetWidth()))
            li = LAYERS.index(item.GetLayer())
            for i, x, y in cells_in(*bbox):
                if f(x, y) <= -0.02:
                    out.add((li, i))
    elif cls == "ZONE":
        L = item.GetLayer()
        if L in LAYERS:
            li = LAYERS.index(L)
            polys = item.GetFilledPolysList(L)
            bb = polys.BBox()
            for i, x, y in cells_in(to_mm(bb.GetLeft()), to_mm(bb.GetTop()),
                                    to_mm(bb.GetRight()), to_mm(bb.GetBottom())):
                if polys.Contains(pcbnew.VECTOR2I(mm(x), mm(y))):
                    out.add((li, i))
    return out


def island_cells(polys, k, li):
    out = set()
    outline = polys.COutline(k)
    holes = [polys.CHole(k, h) for h in range(polys.HoleCount(k))]
    bb = outline.BBox()
    for i, x, y in cells_in(to_mm(bb.GetLeft()), to_mm(bb.GetTop()),
                            to_mm(bb.GetRight()), to_mm(bb.GetBottom())):
        pt = pcbnew.VECTOR2I(mm(x), mm(y))
        if outline.PointInside(pt) and not any(h.PointInside(pt) for h in holes):
            out.add((li, i))
    return out


# --------------------------------------------------------------------------
# A*
# --------------------------------------------------------------------------
def astar(F, net, hw, seeds, goals, via_goal=False, ripup=False):
    nL = len(LAYERS)
    gx = gy = None
    if goals and not via_goal:
        pts = [cell_xy(i) for _, i in goals]
        gx, gy = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)

    def h(i):
        if gx is None:
            return 0.0
        x, y = cell_xy(i)
        dx, dy = abs(x - gx) / G, abs(y - gy) / G
        return max(dx, dy) + (SQ2 - 1) * min(dx, dy)

    best = {}
    parent = {}
    heap = []
    for li, i in seeds:
        if F.track_ok(li, i, net, hw) or (ripup and F.track_fixed_ok(li, i, net, hw)):
            s = li * N + i
            best[s] = 0.0
            parent[s] = None
            heapq.heappush(heap, (h(i), 0.0, s))
    expanded = 0
    while heap:
        f, g, s = heapq.heappop(heap)
        if g > best.get(s, 1e18):
            continue
        li, i = divmod(s, N)
        if via_goal:
            if F.via_ok(i, net) or (ripup and F.via_fixed_ok(i, net)):
                return path_of(parent, s), True
        elif (li, i) in goals:
            return path_of(parent, s), False
        expanded += 1
        if expanded > MAX_EXPAND:
            return None, False
        ix, iy = i % NX, i // NX
        lc = LAYER_COST[li]
        for dx, dy, c in MOVES:
            nx, ny = ix + dx, iy + dy
            if not (0 <= nx < NX and 0 <= ny < NY):
                continue
            ni = ny * NX + nx
            extra = 0.0
            if not F.track_ok(li, ni, net, hw):
                if not (ripup and F.track_fixed_ok(li, ni, net, hw)):
                    continue
                extra = RIP_COST
            ns = li * N + ni
            ng = g + c * lc + extra
            if ng < best.get(ns, 1e18):
                best[ns] = ng
                parent[ns] = s
                heapq.heappush(heap, (ng + h(ni), ng, ns))
        vok = F.via_ok(i, net)
        if vok or (ripup and F.via_fixed_ok(i, net)):
            vcost = VIA_COST if vok else VIA_COST + 3 * RIP_COST
            for l2 in range(nL):
                if l2 == li or not (F.track_ok(l2, i, net, hw)
                                    or (ripup and F.track_fixed_ok(l2, i, net, hw))):
                    continue
                ns = l2 * N + i
                ng = g + vcost
                if ng < best.get(ns, 1e18):
                    best[ns] = ng
                    parent[ns] = s
                    heapq.heappush(heap, (ng + h(i), ng, ns))
    return None, False


def path_of(parent, s):
    out = []
    while s is not None:
        out.append(divmod(s, N))
        s = parent[s]
    return out[::-1]


def to_copper(path, end_via):
    """[(li, i), ...] -> segments [(li, (x0,y0), (x1,y1))] and via points."""
    segs, vias = [], []
    k = 0
    while k < len(path):
        li = path[k][0]
        run = [path[k][1]]
        k += 1
        while k < len(path) and path[k][0] == li:
            run.append(path[k][1])
            k += 1
        if k < len(path):
            vias.append(cell_xy(path[k][1]))
        # merge collinear steps
        pts = [cell_xy(i) for i in run]
        corners = [pts[0]]
        for a in range(1, len(pts) - 1):
            d0 = (round((pts[a][0] - pts[a - 1][0]) / G), round((pts[a][1] - pts[a - 1][1]) / G))
            d1 = (round((pts[a + 1][0] - pts[a][0]) / G), round((pts[a + 1][1] - pts[a][1]) / G))
            if d0 != d1:
                corners.append(pts[a])
        if len(pts) > 1:
            corners.append(pts[-1])
        for a in range(len(corners) - 1):
            segs.append((li, corners[a], corners[a + 1]))
    if end_via:
        vias.append(cell_xy(path[-1][1]))
    return segs, vias


def commit(board, F, net, w, segs, vias):
    ni = board.FindNet(net) if isinstance(net, str) else net
    code = ni.GetNetCode()
    for li, a, b in segs:
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pcbnew.VECTOR2I(mm(a[0]), mm(a[1])))
        t.SetEnd(pcbnew.VECTOR2I(mm(b[0]), mm(b[1])))
        t.SetLayer(LAYERS[li])
        t.SetWidth(mm(w))
        t.SetNet(ni)
        board.Add(t)
        TRACKS.append(t)
        F.add_track(code, li, a[0], a[1], b[0], b[1], w)
    for x, y in vias:
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        v.SetWidth(mm(VIA_D))
        v.SetDrill(mm(VIA_DRILL))
        v.SetNet(ni)
        board.Add(v)
        TRACKS.append(v)
        F.add_via(code, x, y)


def class_width(ni):
    try:
        return to_mm(ni.GetNetClass().GetTrackWidth())
    except Exception:
        return 0.15


def widths_for(ni):
    cw = class_width(ni)
    return [w for w in WIDTHS if w <= cw + 1e-6] or [0.15]




# --------------------------------------------------------------------------
# rip-up: which existing copper a new path runs into, and the wire it is part of
# --------------------------------------------------------------------------
def segseg(a, b, c, d):
    """Distance between segments ab and cd (mm)."""
    def cross(o, p, q):
        return (p[0] - o[0]) * (q[1] - o[1]) - (p[1] - o[1]) * (q[0] - o[0])
    d1, d2, d3, d4 = cross(c, d, a), cross(c, d, b), cross(a, b, c), cross(a, b, d)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)):
        return 0.0
    return min(seg_dist(a[0], a[1], c[0], c[1], d[0], d[1]),
               seg_dist(b[0], b[1], c[0], c[1], d[0], d[1]),
               seg_dist(c[0], c[1], a[0], a[1], b[0], b[1]),
               seg_dist(d[0], d[1], a[0], a[1], b[0], b[1]))


def xy(v):
    return (to_mm(v.x), to_mm(v.y))


def blockers(board, code, w, segs, vias, removed):
    clr = 0.1 + 0.005
    out = []
    for t in list(TRACKS):
        if t.GetNetCode() == code or t.m_Uuid.AsString() in removed:
            continue
        if t.GetClass() == "PCB_VIA":
            p = xy(t.GetPosition())
            vd = to_mm(t.GetWidth(pcbnew.F_Cu))
            hit = any(seg_dist(p[0], p[1], a[0], a[1], b[0], b[1]) < vd / 2 + w / 2 + clr
                      for _, a, b in segs)
            hit = hit or any(math.hypot(p[0] - x, p[1] - y) < (vd + VIA_D) / 2 + clr for x, y in vias)
        else:
            if t.GetLayer() not in LAYERS:
                continue
            li = LAYERS.index(t.GetLayer())
            a0, b0, tw = xy(t.GetStart()), xy(t.GetEnd()), to_mm(t.GetWidth())
            hit = any(segseg(a, b, a0, b0) < (w + tw) / 2 + clr for l2, a, b in segs if l2 == li)
            hit = hit or any(seg_dist(x, y, a0[0], a0[1], b0[0], b0[1]) < VIA_D / 2 + tw / 2 + clr
                             for x, y in vias)
        if hit:
            out.append(t)
    return out


def wire_of(board, item, removed):
    """The item plus the copper chained to it up to the nearest pad, branch
    point or dead end: the stretch that has to go for a path through it."""
    code = item.GetNetCode()
    key = lambda p: (int(round(p[0] * 1000)), int(round(p[1] * 1000)))
    ends, vias = {}, {}
    for t in list(TRACKS):
        if t.GetNetCode() != code or t.m_Uuid.AsString() in removed:
            continue
        if t.GetClass() == "PCB_VIA":
            vias[key(xy(t.GetPosition()))] = t
        else:
            for p in (xy(t.GetStart()), xy(t.GetEnd())):
                ends.setdefault(key(p), []).append(t)
    pads = [p for p in board.GetPads() if p.GetNetCode() == code]

    def pad_at(p, layer):
        v = pcbnew.VECTOR2I(mm(p[0]), mm(p[1]))
        return any(pd.IsOnLayer(layer) and pd.HitTest(v) for pd in pads)

    wire = {item.m_Uuid.AsString(): item}
    if item.GetClass() == "PCB_VIA":
        k = key(xy(item.GetPosition()))
        if len(ends.get(k, [])) > 2:
            return list(wire.values())
        stack = [item]
    else:
        stack = [item]
    while stack:
        it = stack.pop()
        if it.GetClass() == "PCB_VIA":
            k = key(xy(it.GetPosition()))
            for u in ends.get(k, []):
                if u.m_Uuid.AsString() not in wire:
                    wire[u.m_Uuid.AsString()] = u
                    stack.append(u)
            continue
        for p in (xy(it.GetStart()), xy(it.GetEnd())):
            if pad_at(p, it.GetLayer()):
                continue
            k = key(p)
            here = ends.get(k, [])
            v = vias.get(k)
            if v is not None:
                if len(here) <= 2 and v.m_Uuid.AsString() not in wire:
                    wire[v.m_Uuid.AsString()] = v
                    stack.append(v)
                continue
            same = [u for u in here if u.GetLayer() == it.GetLayer()]
            if len(same) == 2:
                for u in same:
                    if u.m_Uuid.AsString() not in wire:
                        wire[u.m_Uuid.AsString()] = u
                        stack.append(u)
    return list(wire.values())


def rip(board, items, removed):
    # collect every wire first: removing an item frees it, and a later
    # blocker on the same wire would then be a dangling pointer
    doomed = {}
    for it in items:
        for u in wire_of(board, it, removed):
            doomed.setdefault(u.m_Uuid.AsString(), u)
    nets = set()
    for uid, u in doomed.items():
        if uid in removed:
            continue
        removed.add(uid)
        nets.add(u.GetNetname())
        board.Remove(u)
        TRACKS[:] = [x for x in TRACKS if x is not u]
    return nets


# --------------------------------------------------------------------------
# routing a pair / a ground island
# --------------------------------------------------------------------------
def try_route(board, F, ni, seeds, goals, via_goal, widths, ripup, removed):
    code = ni.GetNetCode()
    for w in widths:
        path, _ = astar(F, code, w / 2, seeds, goals, via_goal=via_goal, ripup=ripup)
        if not path:
            continue
        segs, vias = to_copper(path, via_goal)
        ripped = set()
        if ripup:
            blk = blockers(board, code, w, segs, vias, removed)
            ripped = rip(board, blk, removed)
        commit(board, F, ni, w, segs, vias)
        msg = f"{w} mm, {len(segs)} segments, {len(vias)} vias"
        if ripped:
            msg += f"; ripped up {', '.join(sorted(n.strip('/') for n in ripped))}"
        return msg
    return None


def route_pair(board, F, a, b, removed, ripup):
    if a.GetClass() == "ZONE" and b.GetClass() != "ZONE":
        a, b = b, a
    ni = a.GetNet()
    seeds, goals = item_cells(board, a), item_cells(board, b)
    if not seeds or not goals:
        return None
    ws = widths_for(ni)
    return try_route(board, F, ni, seeds, goals, False, ws if not ripup else ws[-2:], ripup, removed)


def gnd_islands(board):
    gnd = board.FindNet("/GND")
    code = gnd.GetNetCode()
    through = [t.GetPosition() for t in TRACKS
               if t.GetClass() == "PCB_VIA" and t.GetNetCode() == code]
    through += [p.GetPosition() for p in board.GetPads() if p.HasHole() and p.GetNetCode() == code]
    out = []
    for z in board.Zones():
        if z.GetNetCode() != code or z.GetLayer() not in (pcbnew.F_Cu, pcbnew.B_Cu):
            continue
        li = LAYERS.index(z.GetLayer())
        polys = z.GetFilledPolysList(z.GetLayer())
        for k in range(polys.OutlineCount()):
            outline = polys.COutline(k)
            if any(outline.PointInside(p) for p in through):
                continue
            bb = outline.BBox()
            out.append((f"{pcbnew.LayerName(z.GetLayer())} island at "
                        f"({to_mm(bb.Centre().x):.2f}, {to_mm(bb.Centre().y):.2f})",
                        island_cells(polys, k, li)))
    return out


def unconnected_pairs(pcb):
    out = os.path.join(tempfile.gettempdir(), "handroute_drc.json")
    subprocess.run([CLI, "pcb", "drc", "--format", "json", "--severity-error", "-o", out, pcb],
                   check=True, capture_output=True)
    d = json.load(open(out, encoding="utf8"))
    errors = [v for v in d["violations"] if v.get("severity") == "error"]
    return [[it["uuid"] for it in u["items"]] for u in d["unconnected_items"]], errors


def label(it):
    fp = it.GetParentFootprint() if it.GetClass() == "PAD" else None
    return f"{fp.GetReference()}.{it.GetNumber()}" if fp else it.GetClass().replace("PCB_", "").lower()


def one_round(pcb, pairs):
    board = pcbnew.LoadBoard(pcb)
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    # Our own track list from here on: after many Add/Remove calls KiCad 10's
    # SWIG wrapper stops returning a usable list from board.GetTracks().
    TRACKS[:] = list(board.GetTracks())
    by_id = {it.m_Uuid.AsString(): it
             for it in list(board.GetPads()) + TRACKS + list(board.Zones())}
    F = build_field(board)
    removed = set()
    jobs = []
    for ua, ub in pairs:
        a, b = by_id.get(ua), by_id.get(ub)
        if a is None or b is None or a.GetNetname() == "/GND":
            continue                            # GND: islands, below
        pa, pb = a.GetPosition(), b.GetPosition()
        jobs.append((math.hypot(to_mm(pa.x - pb.x), to_mm(pa.y - pb.y)), ua, ub))
    jobs.sort()
    failed = []
    for _, ua, ub in jobs:                      # 1. around existing copper
        if ua in removed or ub in removed:
            continue
        a, b = by_id[ua], by_id[ub]
        res = route_pair(board, F, a, b, removed, False)
        print(f"    {a.GetNetname():14s} {label(a):>8s} -> {label(b):<8s} "
              f"{res or 'blocked'}", flush=True)
        if not res:
            failed.append((ua, ub))
    for ua, ub in failed:                       # 2. through rippable copper
        if ua in removed or ub in removed:
            continue
        a, b = by_id[ua], by_id[ub]
        res = route_pair(board, F, a, b, removed, True)
        print(f"    {a.GetNetname():14s} {label(a):>8s} -> {label(b):<8s} "
              f"rip-up: {res or 'NO PATH'}", flush=True)
    gnd = board.FindNet("/GND")
    for where, seeds in gnd_islands(board):     # 3. ground islands -> via to In1
        res = try_route(board, F, gnd, seeds, None, True, (0.3, 0.2, 0.15), False, removed) \
            or try_route(board, F, gnd, seeds, None, True, (0.15,), True, removed)
        print(f"    /GND {where}: {res or 'NO PATH'}", flush=True)
    filler.Fill(board.Zones())
    board.Save(pcb)


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else ""
    if name not in ("fc", "vision"):
        raise SystemExit("usage: handroute.py fc|vision")
    pcb = os.path.join(HERE, f"{name}.kicad_pcb")
    best_file = os.path.join(HERE, ".routing", f"{name}_handroute_best.kicad_pcb")
    os.makedirs(os.path.dirname(best_file), exist_ok=True)
    if "--one-round" in sys.argv:
        # one round in a fresh process: KiCad 10's SWIG wrapper degrades after
        # many edits in one session (board lists come back as raw pointers)
        pairs, _ = unconnected_pairs(pcb)
        one_round(pcb, pairs)
        return
    best = None
    for r in range(ROUNDS + 1):
        pairs, errors = unconnected_pairs(pcb)
        # a short or clearance error always loses; thermal-relief errors count
        # the same as an open connection (both are one small fix)
        hard = [e for e in errors if e["type"] != "starved_thermal"]
        score = (len(hard), len(pairs) + len(errors) - len(hard))
        kinds = sorted({e["type"] for e in errors})
        print(f">>> round {r}: {len(pairs)} unconnected, {len(errors)} DRC errors"
              + (f" ({', '.join(kinds)})" if kinds else ""), flush=True)
        shutil.copyfile(pcb, best_file.replace("_best", f"_round{r}"))
        if best is None or score < best:
            best = score
            shutil.copyfile(pcb, best_file)
        if not pairs or r == ROUNDS:
            break
        subprocess.run([sys.executable, "-X", "faulthandler", os.path.abspath(__file__),
                        name, "--one-round"], cwd=HERE)
    shutil.copyfile(best_file, pcb)
    print(f">>> kept the best round: {best[1]} open (unconnected + thermal), {best[0]} other DRC errors")


if __name__ == "__main__":
    main()
