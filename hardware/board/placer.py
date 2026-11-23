"""
DroneKit Pro - the placement engine shared by place_fc.py and place_vision.py.

Each board's script lists FIXED parts (exact spot) and NEAR parts (as close as
they fit to an anchor pad), then calls run(). The engine:

  - keeps every courtyard inside the board, clear of the rounded corners and
    EDGE_INSET from the edge (copper-to-edge rule), except "edge" parts,
    which are pushed flush to their edge with their opening facing out;
  - never lets two courtyards overlap on a side, and treats through-hole
    pins and keep-out areas (the ESP32-S3 antenna) as blocking both sides;
  - walks outward from each anchor in STEP rings, trying 0 and 90 degrees,
    and takes the first free spot; it stops with a clear message (and saves
    the partial board as <board>-partial.kicad_pcb) when a part won't fit;
  - lists every part it had to put more than 4 mm from its anchor;
  - hides the silkscreen reference of every part not in silk_labels.

Coordinates are mm from the board centre in KiCad axes: +x = front (camera
side), +y = the board's right side looking forward.
"""

import math
import os

import pcbnew

ORIGIN = (150.0, 100.0)
HALF_W, HALF_H = 16.0, 15.0
CORNER_R = 2.0                      # board corner radius (build_pcb.py)
EDGE_INSET = 0.15                   # courtyard to edge: small parts' courtyards are only
                                    # ~0.2 mm past their pads, the copper-to-edge rule is 0.25
MAX_R = 14.0
STEP = 0.25
TOP, BOT = "top", "bottom"
POWER_NETS = {"GND", "+3V3_SYS", "+3V3_ESP", "+3V8", "VBAT", "VBAT_RAW",
              "+2V8_CAM", "+1V2_CAM"}


def mm(v):
    return pcbnew.FromMM(v)


def to_mm(v):
    return pcbnew.ToMM(v)


class Rect:
    __slots__ = ("x0", "y0", "x1", "y1", "who")

    def __init__(self, x0, y0, x1, y1, who=""):
        self.x0, self.y0, self.x1, self.y1, self.who = x0, y0, x1, y1, who

    def hits(self, o):
        return self.x0 < o.x1 and o.x0 < self.x1 and self.y0 < o.y1 and o.y0 < self.y1

    def moved(self, dx, dy, who=""):
        return Rect(self.x0 + dx, self.y0 + dy, self.x1 + dx, self.y1 + dy, who)

    def __repr__(self):
        return f"{self.who}[{self.x0:.2f}..{self.x1:.2f}, {self.y0:.2f}..{self.y1:.2f}]"


class Placer:
    def __init__(self, board, edge_overhang=None):
        self.board = board
        self.edge_overhang = edge_overhang or {}
        self.fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
        self.occ = {TOP: [], BOT: []}
        self.placed = set()

    # --- geometry of a footprint at (side, rot), relative to its anchor point
    def set_side_rot(self, fp, side, rot):
        if fp.IsFlipped() != (side == BOT):
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        fp.SetOrientationDegrees(rot)

    def shapes(self, fp, side):
        """Courtyard rect on its own side + through-hole pad rects (both sides),
        all relative to fp position, in mm."""
        o = fp.GetPosition()
        layer = pcbnew.B_CrtYd if side == BOT else pcbnew.F_CrtYd
        c = fp.GetCourtyard(layer)
        bb = c.BBox() if c.OutlineCount() else fp.GetBoundingBox(False)
        own = Rect(to_mm(bb.GetLeft() - o.x), to_mm(bb.GetTop() - o.y),
                   to_mm(bb.GetRight() - o.x), to_mm(bb.GetBottom() - o.y))
        holes = []
        for p in fp.Pads():
            if p.HasHole():
                pb = p.GetBoundingBox()
                holes.append(Rect(to_mm(pb.GetLeft() - o.x) - 0.25, to_mm(pb.GetTop() - o.y) - 0.25,
                                  to_mm(pb.GetRight() - o.x) + 0.25, to_mm(pb.GetBottom() - o.y) + 0.25))
        return own, holes

    @staticmethod
    def inside_corners(r):
        """All four rect corners inside the rounded board outline."""
        cx, cy = HALF_W - CORNER_R, HALF_H - CORNER_R
        for px, py in ((r.x0, r.y0), (r.x1, r.y0), (r.x0, r.y1), (r.x1, r.y1)):
            dx, dy = abs(px) - cx, abs(py) - cy
            if dx > 0 and dy > 0 and dx * dx + dy * dy > CORNER_R * CORNER_R:
                return False
        return True

    def fits(self, ref, side, own, holes, x, y, allow_edge=0.0):
        r = own.moved(x, y)
        e = allow_edge if allow_edge else -EDGE_INSET
        if (r.x0 < -HALF_W - e or r.x1 > HALF_W + e or r.y0 < -HALF_H - e or r.y1 > HALF_H + e):
            return False
        if not allow_edge and not self.inside_corners(Rect(r.x0 - EDGE_INSET, r.y0 - EDGE_INSET,
                                                           r.x1 + EDGE_INSET, r.y1 + EDGE_INSET)):
            return False
        if any(r.hits(o) for o in self.occ[side]):
            return False
        other = BOT if side == TOP else TOP
        for h in holes:
            hm = h.moved(x, y)
            if any(hm.hits(o) for o in self.occ[other]):
                return False
        return True

    def why(self, side, own, holes, x, y):
        """What a placement would hit (for error messages)."""
        r = own.moved(x, y, "this")
        hit = [o for o in self.occ[side] if r.hits(o)]
        other = BOT if side == TOP else TOP
        for h in holes:
            hm = h.moved(x, y)
            hit += [o for o in self.occ[other] if hm.hits(o)]
        return f"{r} hits {hit}"

    def commit(self, fp, side, own, holes, x, y):
        fp.SetPosition(pcbnew.VECTOR2I(mm(ORIGIN[0] + x), mm(ORIGIN[1] + y)))
        ref = fp.GetReference()
        for z in fp.Zones():           # keep-out areas (U2's antenna): both sides
            bb = z.GetBoundingBox()
            kz = Rect(to_mm(bb.GetLeft()) - ORIGIN[0], to_mm(bb.GetTop()) - ORIGIN[1],
                      to_mm(bb.GetRight()) - ORIGIN[0], to_mm(bb.GetBottom()) - ORIGIN[1],
                      ref + " keep-out")
            self.occ[TOP].append(kz)
            self.occ[BOT].append(kz)
        self.occ[side].append(own.moved(x, y, ref))
        other = BOT if side == TOP else TOP
        for h in holes:
            self.occ[other].append(h.moved(x, y, ref + " pin"))
        self.placed.add(fp.GetReference())

    # --- pass 0: things already fixed by build_pcb.py (holes, J200)
    def take_existing(self, refs):
        for ref in refs:
            fp = self.fps[ref]
            side = BOT if fp.IsFlipped() else TOP
            own, holes = self.shapes(fp, side)
            p = fp.GetPosition()
            x, y = to_mm(p.x) - ORIGIN[0], to_mm(p.y) - ORIGIN[1]
            self.occ[side].append(own.moved(x, y, ref))
            if ref.startswith("H"):                    # hole keep-out: both sides
                self.occ[BOT if side == TOP else TOP].append(own.moved(x, y, ref))
            for h in holes:
                self.occ[BOT if side == TOP else TOP].append(h.moved(x, y, ref + " pin"))
            self.placed.add(ref)

    # --- pass 1
    def place_fixed(self, ref, spec):
        fp = self.fps[ref]
        side = spec[0]
        if spec[1] == "edge":
            edge, along = spec[2], spec[3]
            # The opening faces away from the signal pads. Try the rotation
            # that should point it at the edge, and the opposite one (a part
            # on the bottom is mirrored), and keep the one whose pads sit on
            # the inner side.
            out = {"-x": (-1, 0), "+x": (1, 0), "-y": (0, -1), "+y": (0, 1)}[edge]
            base = {"-x": 270, "+x": 90, "-y": 180, "+y": 0}[edge]
            for rot in (base, (base + 180) % 360):
                self.set_side_rot(fp, side, rot)
                own, holes = self.shapes(fp, side)
                o = fp.GetPosition()
                sig = [p for p in fp.Pads() if p.GetNumber() not in ("", "MP", "SH")]
                px = sum(to_mm(p.GetPosition().x - o.x) for p in sig) / len(sig)
                py = sum(to_mm(p.GetPosition().y - o.y) for p in sig) / len(sig)
                cx, cy = (own.x0 + own.x1) / 2, (own.y0 + own.y1) / 2
                if (cx - px) * out[0] + (cy - py) * out[1] > 0:
                    break
            else:
                raise SystemExit(f"FIXED {ref}: can't tell which way it opens")
            over = self.edge_overhang.get(ref, 0.0)
            if edge == "-x":
                x, y = -HALF_W - over - own.x0, along
            elif edge == "+x":
                x, y = HALF_W + over - own.x1, along
            elif edge == "-y":
                x, y = along, -HALF_H - over - own.y0
            else:
                x, y = along, HALF_H + over - own.y1
            allow = max(over, 1e-6)        # edge part: may touch (or overhang) its edge
        else:
            _, x, y, rot = spec
            self.set_side_rot(fp, side, rot)
            own, holes = self.shapes(fp, side)
            allow = self.edge_overhang.get(ref, 0.0)   # e.g. an antenna past the edge
        if not self.fits(ref, side, own, holes, x, y, allow):
            raise SystemExit(f"FIXED {ref} at ({x:.2f}, {y:.2f}) {side}: "
                             + self.why(side, own, holes, x, y))
        self.commit(fp, side, own, holes, x, y)

    # --- pass 2
    def pad_xy(self, spec):
        ref, num = spec.split(".")
        fp = self.fps[ref]
        if ref not in self.placed:
            raise SystemExit(f"anchor {spec}: {ref} isn't placed yet (order NEAR)")
        for p in fp.Pads():
            if p.GetNumber() == num:
                q = p.GetPosition()
                return to_mm(q.x) - ORIGIN[0], to_mm(q.y) - ORIGIN[1]
        raise SystemExit(f"anchor {spec}: no pad {num}")

    def auto_anchor(self, ref):
        fp = self.fps[ref]
        for p in fp.Pads():
            n = p.GetNetname().lstrip("/")
            if not n or n in POWER_NETS or n.startswith("unconnected"):
                continue
            best = None
            for other in self.board.GetFootprints():
                oref = other.GetReference()
                if oref == ref or oref[0] in "RC" or oref not in self.placed:
                    continue
                for op in other.Pads():
                    if op.GetNetname() == p.GetNetname():
                        best = op
                        break
                if best:
                    break
            if best:
                q = best.GetPosition()
                return to_mm(q.x) - ORIGIN[0], to_mm(q.y) - ORIGIN[1]
        return None

    def place_near(self, ref, side, anchor, other_ok):
        fp = self.fps[ref]
        ax, ay = self.pad_xy(anchor) if isinstance(anchor, str) else anchor
        sides = [side] + ([BOT if side == TOP else TOP] if other_ok else [])
        for s in sides:
            geo = []
            for rot in (0, 90):
                self.set_side_rot(fp, s, rot)
                geo.append((rot,) + self.shapes(fp, s))
            r = 0.0
            while r <= MAX_R:
                n = max(1, int(2 * math.pi * r / STEP))
                for k in range(n):
                    a = 2 * math.pi * k / n
                    x = round((ax + r * math.cos(a)) / 0.05) * 0.05
                    y = round((ay + r * math.sin(a)) / 0.05) * 0.05
                    for rot, own, holes in geo:
                        if self.fits(ref, s, own, holes, x, y):
                            self.set_side_rot(fp, s, rot)
                            self.commit(fp, s, own, holes, x, y)
                            return s, r
                r += STEP
        raise SystemExit(f"NEAR {ref}: no free spot within {MAX_R} mm of {anchor} on {sides}")


def run(pcb, fixed, near, silk_labels, edge_overhang=None, preplaced=("J200", "J201")):
    board = pcbnew.LoadBoard(pcb)
    try:
        _place_all(board, pcb, fixed, near, silk_labels, edge_overhang, preplaced)
    except SystemExit:
        partial = pcb.replace(".kicad_pcb", "-partial.kicad_pcb")
        board.Save(partial)
        print(f"!!! stopped; what was placed so far is in {os.path.basename(partial)}")
        raise
    for junk in (pcb.replace(".kicad_pcb", "-partial.kicad_pcb"),
                 pcb.replace(".kicad_pcb", "-partial.kicad_pro")):
        if os.path.exists(junk):
            os.remove(junk)


def _place_all(board, pcb, fixed, near, silk_labels, edge_overhang, preplaced):
    pl = Placer(board, edge_overhang)
    pl.take_existing([r for r in pl.fps if r.startswith("H") or r in preplaced])
    for ref, spec in fixed.items():
        pl.place_fixed(ref, spec)
    far = []
    for ref, (side, anchor, other_ok) in near.items():
        s, r = pl.place_near(ref, side, anchor, other_ok)
        if r > 4.0 or s != side:
            far.append(f"{ref} {r:.1f} mm from {anchor} ({s})")
    # everything else: anchor on the pad it serves
    rest = sorted((r for r in pl.fps if r not in pl.placed),
                  key=lambda r: -len(pl.fps[r].Pads()))
    for ref in rest:
        a = pl.auto_anchor(ref)
        if a is None:
            raise SystemExit(f"{ref}: no anchor; add it to NEAR")
        s, r = pl.place_near(ref, TOP, a, True)
        if r > 4.0:
            far.append(f"{ref} {r:.1f} mm from its pin ({s})")
    for fp in board.GetFootprints():
        if not fp.GetReference().startswith("H"):
            fp.Reference().SetVisible(fp.GetReference() in silk_labels)
    board.Save(pcb)
    parts = [f for f in board.GetFootprints() if not f.GetReference().startswith("H")]
    top = sum(1 for f in parts if not f.IsFlipped())
    print(f">>> placed {len(parts)} parts: {top} top, {len(parts) - top} bottom")
    if far:
        print(">>> placed more than 4 mm from their anchor (check these):")
        for f in far:
            print("    " + f)
