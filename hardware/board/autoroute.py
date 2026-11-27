"""
DroneKit Pro - autoroute one board with Freerouting.

Run with KiCad's own Python, after placement and route_setup.py:

    "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" autoroute.py fc start [--inner2]
    ... wait for .routing/fc.ses (Freerouting runs as its own process) ...
    "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" autoroute.py fc finish

Needs Java 21+ and freerouting.jar 2.1.0 (the last release that runs on
Java 21) at FREEROUTING_JAR or ~/.kicad-mcp/freerouting.jar.

Freerouting 2.1 doesn't honour a pass limit given on the command line; cap
it in its own settings file (%TEMP%/freerouting/freerouting.json:
router.max_passes, router.job_timeout).

Steps:
  1. Mark In1.Cu (and, without --inner2, In2.Cu) as power planes. KiCad's Specctra export passes
     that on, and Freerouting then reaches the GND / 3.3 V planes with vias
     instead of cutting them up with tracks: signals go on F.Cu and B.Cu.
  2. Fill the zones and export <board>.dsn.
  3. Run Freerouting headless (net-class track widths and clearances come
     through the DSN).
  4. Import the routed <board>.ses, refill the zones, save <board>.kicad_pcb.

Existing tracks and vias are kept as fixed obstacles, so hand-routed nets
(the power loops) can be routed first and survive. The .dsn/.ses files are
written to a temp folder and removed.
"""

import glob
import os
import subprocess
import sys
import tempfile

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
JAR = os.environ.get("FREEROUTING_JAR",
                     os.path.join(os.path.expanduser("~"), ".kicad-mcp", "freerouting.jar"))


def find_java():
    for pat in (r"C:\Program Files\Eclipse Adoptium\*\bin\java.exe",
                r"C:\Program Files\Java\*\bin\java.exe"):
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[-1]
    return "java"


WORK = os.path.join(HERE, ".routing")      # dsn / ses / log live here (git-ignored)
DETACHED = 0x00000008 | 0x00000200        # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
BREAKAWAY = 0x01000000                    # CREATE_BREAKAWAY_FROM_JOB


def start(name, inner2):
    """Export the DSN and launch Freerouting as its own process, so a run
    survives this shell (and an app restart). Its result lands in
    .routing/<name>.ses; collect it with `finish`."""
    os.makedirs(WORK, exist_ok=True)
    pcb = os.path.join(HERE, f"{name}.kicad_pcb")
    board = pcbnew.LoadBoard(pcb)
    board.SetLayerType(board.GetLayerID("In1.Cu"), pcbnew.LT_POWER)
    if inner2:
        # Route on In2 too: take its 3.3 V fill out of the exported copy only
        # (the saved board keeps it; it refills around the new tracks).
        for z in list(board.Zones()):
            if z.GetLayer() == board.GetLayerID("In2.Cu") and not z.GetIsRuleArea():
                board.Remove(z)
        board.SetLayerType(board.GetLayerID("In2.Cu"), pcbnew.LT_SIGNAL)
    else:
        board.SetLayerType(board.GetLayerID("In2.Cu"), pcbnew.LT_POWER)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    dsn, ses, log = (os.path.join(WORK, f"{name}.{e}") for e in ("dsn", "ses", "log"))
    for f in (ses,):
        if os.path.exists(f):
            os.remove(f)
    if not pcbnew.ExportSpecctraDSN(board, dsn):
        raise SystemExit("Specctra DSN export failed")
    cmd = [find_java(), "-jar", JAR, "-de", dsn, "-do", ses, "--gui.enabled=false"]
    out = open(log, "w")
    try:
        proc = subprocess.Popen(cmd, stdout=out, stderr=subprocess.STDOUT,
                                creationflags=DETACHED | BREAKAWAY, cwd=WORK)
    except OSError:
        proc = subprocess.Popen(cmd, stdout=out, stderr=subprocess.STDOUT,
                                creationflags=DETACHED, cwd=WORK)
    open(os.path.join(WORK, f"{name}.pid"), "w").write(str(proc.pid))
    print(f">>> Freerouting started (pid {proc.pid}){' with In2.Cu as a routing layer' if inner2 else ''}; "
          f"result -> .routing/{name}.ses, log -> .routing/{name}.log")


def fix_small_vias(board):
    """The SES import gives every via its net class's drill, so 0.45 mm GND
    stitching vias come back with the Power class's 0.3 mm drill (0.075 mm
    annular ring). Put any via under 0.6 mm back to a 0.2 mm drill."""
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA" and t.GetWidth(pcbnew.F_Cu) < pcbnew.FromMM(0.6) \
                and t.GetDrillValue() > pcbnew.FromMM(0.2):
            t.SetDrill(pcbnew.FromMM(0.2))


def finish(name):
    """Import .routing/<name>.ses into <name>.kicad_pcb and refill zones."""
    ses = os.path.join(WORK, f"{name}.ses")
    if not os.path.exists(ses):
        raise SystemExit(f"no {ses} yet: Freerouting hasn't finished (see .routing/{name}.log)")
    pcb = os.path.join(HERE, f"{name}.kicad_pcb")
    board = pcbnew.LoadBoard(pcb)
    before = len(board.GetTracks())
    if not pcbnew.ImportSpecctraSES(board, ses):
        raise SystemExit("Specctra SES import failed")
    fix_small_vias(board)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(pcb)
    tracks = board.GetTracks()
    vias = sum(1 for t in tracks if t.GetClass() == "PCB_VIA")
    print(f">>> {name}: {len(tracks) - vias} track segments, {vias} vias "
          f"(was {before} items before import)")


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else ""
    step = sys.argv[2] if len(sys.argv) > 2 else ""
    if name not in ("fc", "vision") or step not in ("start", "finish"):
        raise SystemExit("usage: autoroute.py fc|vision start [--inner2] | finish")
    if not os.path.exists(JAR):
        raise SystemExit(f"freerouting.jar not found at {JAR}")
    if step == "start":
        start(name, "--inner2" in sys.argv)
    else:
        finish(name)


if __name__ == "__main__":
    main()
