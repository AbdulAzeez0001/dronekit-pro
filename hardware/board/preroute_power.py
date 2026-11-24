"""
DroneKit Pro - route the high-current nets first, wide, before anything else.

Run with KiCad's own Python, on the placed board, right after route_setup.py
and before autoroute.py:

    "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" preroute_power.py fc

The motors run straight off the battery: about 2.5 A per motor at full
throttle, about 10 A through VBAT_RAW. Routed after the signals, these nets
only get the 0.8 mm the signals leave them. Routed first, on an empty board,
they get the width they need. The later steps (Freerouting, fanout.py,
handroute.py) treat these tracks as fixed and route around them, and
power_pour.py widens them further at the end.

Each connection below is routed with handroute.py's maze search, widest
width first, on F.Cu / B.Cu (In2.Cu, 0.5 oz, is priced out), with 0.6/0.3 mm
power vias. A connection starts from every piece of its net already routed,
so the branches share one trunk out of the battery pads.
"""

import os
import sys

import pcbnew

import handroute as hr

HERE = os.path.dirname(os.path.abspath(__file__))

# (net, pad to reach, widths to try in mm). Routed in this order; the first
# connection of a net starts from FIRST[net].
FIRST = {"/VBAT_RAW": "J10.1", "/M1_NEG": "J40.2", "/M2_NEG": "J41.2",
         "/M3_NEG": "J42.2", "/M4_NEG": "J43.2", "/VBAT": "Q10.2"}
# Widths for 20 degC rise on 1 oz outer copper (IPC-2221): 2.0 mm carries
# about 5 A (one side of the board, two motors), 1.0 mm about 2.9 A (one
# motor). Wider than this leaves the signals too little room (a 2.5 mm
# everywhere try left Freerouting 26 connections short).
SIDE = (2.0, 1.6, 1.2)                      # battery -> first motor of a side: 5 A
ONE = (1.0, 0.8)                            # a single motor: 2.5 A
JOBS = [
    # battery -> rear motors (each the trunk of its side), then front motors
    ("/VBAT_RAW", "J43.1", SIDE), ("/VBAT_RAW", "J42.1", SIDE),
    ("/VBAT_RAW", "J41.1", ONE), ("/VBAT_RAW", "J40.1", ONE),
    # flyback diodes: the motor current flows in them as the FET turns off
    ("/VBAT_RAW", "D43.1", ONE), ("/VBAT_RAW", "D41.1", ONE),
    ("/VBAT_RAW", "D42.1", ONE), ("/VBAT_RAW", "D40.1", ONE),
    # reverse-polarity FET (buck-boost input, about 1.5 A) and bulk caps
    ("/VBAT_RAW", "Q10.3", (0.8, 0.6)),
    ("/VBAT_RAW", "C40.1", (0.6, 0.4)), ("/VBAT_RAW", "C41.1", (0.6, 0.4)),
    ("/VBAT", "U10.12", (0.8, 0.6)),
    # motor - : pad -> diode -> FET drain, 2.5 A
    ("/M1_NEG", "D40.2", ONE), ("/M1_NEG", "Q40.3", ONE),
    ("/M2_NEG", "D41.2", ONE), ("/M2_NEG", "Q41.3", ONE),
    ("/M3_NEG", "D42.2", ONE), ("/M3_NEG", "Q42.3", ONE),
    ("/M4_NEG", "D43.2", ONE), ("/M4_NEG", "Q43.3", ONE),
]


MAX_VIAS = 3                                # per connection, unless it's the last width


def pad(board, ref_pad):
    ref, num = ref_pad.split(".")
    for p in board.FindFootprintByReference(ref).Pads():
        if p.GetNumber() == num:
            return p
    raise SystemExit(f"no pad {ref_pad}")


def net_cells(board, code):
    """Every cell already covered by this net's routed copper or pads that
    have been reached."""
    out = set()
    for t in hr.TRACKS:
        if t.GetNetCode() == code:
            out |= hr.item_cells(board, t)
    return out


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else ""
    if name != "fc":
        raise SystemExit("usage: preroute_power.py fc")
    pcb = os.path.join(HERE, f"{name}.kicad_pcb")
    board = pcbnew.LoadBoard(pcb)
    # wide tracks need the clearance map to reach further than the 0.62 mm
    # the signal router uses; power vias are 0.6 / 0.3 mm
    hr.R = 1.6
    hr.VIA_D, hr.VIA_DRILL = 0.6, 0.3
    hr.LAYER_COST = [1.0, 60.0, 1.0]
    hr.VIA_COST = 200                    # a layer change costs 10 mm of track
    hr.MAX_EXPAND = 3000000
    hr.TRACKS[:] = list(board.GetTracks())
    F = hr.build_field(board)
    reached = {}
    failed = []
    for net, target, widths in JOBS:
        ni = board.FindNet(net)
        code = ni.GetNetCode()
        seeds = net_cells(board, code)
        reached.setdefault(net, set()).add(FIRST[net])
        for rp in reached[net]:
            seeds |= hr.item_cells(board, pad(board, rp))
        goal = pad(board, target)
        goals = hr.item_cells(board, goal)
        if seeds & goals:
            print(f"    {net:10s} -> {target:7s} already joined")
            reached[net].add(target)
            continue
        done = None
        for k, w in enumerate(widths):
            path, _ = hr.astar(F, code, w / 2, seeds, goals)
            if path:
                segs, vias = hr.to_copper(path, False)
                if len(vias) > MAX_VIAS and k < len(widths) - 1:
                    continue                    # every via squeezes the current: go narrower
                hr.commit(board, F, ni, w, segs, vias)
                for x, y in vias:                         # the map, at the real via size
                    F.add_via(code, x, y, True, hr.VIA_D, hr.VIA_DRILL)
                done = f"{w} mm, {len(segs)} segments, {len(vias)} vias"
                break
        print(f"    {net:10s} -> {target:7s} {done or 'NO PATH'}", flush=True)
        if done:
            reached[net].add(target)
        else:
            failed.append(f"{net} -> {target}")
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(pcb)
    print(f">>> {name}: power routed" + (f"; left for the routers: {', '.join(failed)}" if failed else ""))


if __name__ == "__main__":
    main()
