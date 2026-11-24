"""Write the JLCPCB order files for one or both boards.

    "C:\Program Files\KiCad\10.0\bin\python.exe" make_fab.py      # fc and vision
    "C:\Program Files\KiCad\10.0\bin\python.exe" make_fab.py fc

For each board, fab/<board>/ gets:
  <board>_gerbers.zip   4-layer Gerbers + Excellon drill (upload as the PCB)
  <board>_bom.csv       JLCPCB BOM: Comment, Designator, Footprint, LCSC
  <board>_cpl.csv       JLCPCB placement: Designator, Mid X, Mid Y, Layer, Rotation
  <board>_drc.rpt       KiCad DRC (errors only, with schematic parity)

The script stops if DRC finds any error. Solder-pad "connectors" (battery,
motors, receiver, SWD...) are bare copper, so they're left out of the BOM
and the CPL.

LCSC numbers: only parts whose number has been checked are filled in
(LCSC below). The rest are left blank, so JLCPCB's BOM tool asks for a
match on upload instead of silently fitting a guess. See
"Ordering from JLCPCB" in README.md.
"""
import csv
import pathlib
import subprocess
import sys
import tempfile
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
KICAD_CLI = pathlib.Path(r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe")

LAYERS = ("F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,"
          "F.Mask,B.Mask,Edge.Cuts")

# Footprints that are bare copper on the board: no part to buy or place.
# (The position file gives the footprint name without its library.)
NO_PART_PREFIXES = ("SolderPads_",)

# Footprints whose origin is pin 1, not the part's centre. JLCPCB places
# at the part's centre, so the CPL uses the centre of their pads instead.
CENTRE_FROM_PADS = ("J200", "J201")

# Value -> LCSC number. Sources: docs/bom-cost.md (LCSC listings,
# 2026-11-23), hardware/board/README.md (B2B pair), and JLCPCB's part page
# for C1525 (checked 2026-11-24).
LCSC = {
    "STM32F405RGT6": "C15742",
    "ESP32-S3-WROOM-1-N8R2": "C2913204",
    "ICM-42688-P": "C1850418",
    "SPA06-003": "C30589048",
    "TPS63070RNM": "C109322",
    "TS3USB221A": "C128396",          # TI part, not the HXY clone
    "AP7361C-33E": "C500795",         # -33E-13, not -33ER (reversed pinout)
    "RT9013-33GB": "C47773",
    "XC6206P282MR": "C347374",
    "XC6206P122MR": "C2827649",       # not the Torex -G C424699 (60 mA)
    "USBLC6-2SC6": "C7519",
    "AO3400A": "C20917",
    "AO3401A": "C15127",
    "SS34": "C8678",
    "B5819W": "C8598",
    "USB-C": "C165948",
    "SENSOR_I2C": "C160404",          # JST SM04B-SRSS-TB
    "UART3": "C160404",
    "CODE_I2C": "C160404",
    "B2B_HEADER_2x12_1.27mm": "C5372816",   # HCTL PZ127-2-12-Z
    "B2B_SOCKET_2x12_1.27mm": "C5380281",   # HCTL PM127-2-12-Z-4.3-G0
    "100nF": "C1525",                 # Samsung CL05B104KO5NNNC, 0402 16 V X7R
}

# Parts that must not be ordered yet, with the reason.
ON_HOLD = {
    "J30": "camera FPC: contact side not confirmed (hardware/camera/camera-design.md)",
}


def run(*args):
    r = subprocess.run([str(KICAD_CLI), *map(str, args)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"kicad-cli {args[0]} {args[1]} failed:\n{r.stdout}\n{r.stderr}")
    return r.stdout


def drc(board, out):
    run("pcb", "drc", "--schematic-parity", "--severity-error",
        "--exit-code-violations", "-o", out, HERE / f"{board}.kicad_pcb")


def gerbers(board, out_zip):
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        run("pcb", "export", "gerbers", "-o", tmp, "-l", LAYERS,
            "--subtract-soldermask", "--no-x2", HERE / f"{board}.kicad_pcb")
        run("pcb", "export", "drill", "-o", tmp, "--format", "excellon",
            "-u", "mm", "--excellon-separate-th", HERE / f"{board}.kicad_pcb")
        files = sorted(p for p in tmp.iterdir() if p.is_file())
        with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
            for p in files:
                z.write(p, p.name)
        return [p.name for p in files]


def positions(board):
    with tempfile.TemporaryDirectory() as tmp:
        pos = pathlib.Path(tmp) / "pos.csv"
        run("pcb", "export", "pos", "--format", "csv", "--units", "mm",
            "--side", "both", "-o", pos, HERE / f"{board}.kicad_pcb")
        with open(pos, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))


def is_part(row):
    return not row["Package"].startswith(NO_PART_PREFIXES)


def pad_centre_offsets(board):
    """Pad-centre minus origin, in position-file mm (Y up), for CENTRE_FROM_PADS."""
    import pcbnew
    brd = pcbnew.LoadBoard(str(HERE / f"{board}.kicad_pcb"))
    out = {}
    for fp in brd.GetFootprints():
        if fp.GetReference() not in CENTRE_FROM_PADS:
            continue
        pads = list(fp.Pads())
        bb = pcbnew.BOX2I(pads[0].GetBoundingBox().GetOrigin(),
                          pads[0].GetBoundingBox().GetSize())
        for p in pads[1:]:
            bb.Merge(p.GetBoundingBox())
        c, o = bb.GetCenter(), fp.GetPosition()
        out[fp.GetReference()] = (pcbnew.ToMM(c.x - o.x), -pcbnew.ToMM(c.y - o.y))
    return out


def write_bom_cpl(board, rows, bom_path, cpl_path, offsets):
    parts = [r for r in rows if is_part(r) and r["Ref"] not in ON_HOLD]
    groups = {}
    for r in parts:
        groups.setdefault((r["Val"], r["Package"]), []).append(r["Ref"])

    def refkey(ref):
        head = ref.rstrip("0123456789")
        return head, int(ref[len(head):] or 0)

    missing = []
    with open(bom_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC"])
        for (val, pkg), refs in sorted(groups.items(),
                                       key=lambda kv: refkey(min(kv[1], key=refkey))):
            refs.sort(key=refkey)
            lcsc = LCSC.get(val, "")
            if not lcsc:
                missing.append((val, pkg, refs))
            w.writerow([val, ",".join(refs), pkg, lcsc])

    with open(cpl_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for r in sorted(parts, key=lambda r: refkey(r["Ref"])):
            layer = "Top" if r["Side"] == "top" else "Bottom"
            dx, dy = offsets.get(r["Ref"], (0.0, 0.0))
            w.writerow([r["Ref"], f'{float(r["PosX"]) + dx:.4f}mm',
                        f'{float(r["PosY"]) + dy:.4f}mm', layer,
                        f'{float(r["Rot"]):g}'])
    return parts, groups, missing


def make(board):
    out = HERE / "fab" / board
    out.mkdir(parents=True, exist_ok=True)
    drc(board, out / f"{board}_drc.rpt")
    files = gerbers(board, out / f"{board}_gerbers.zip")
    rows = positions(board)
    parts, groups, missing = write_bom_cpl(
        board, rows, out / f"{board}_bom.csv", out / f"{board}_cpl.csv",
        pad_centre_offsets(board))
    sides = {s: sum(1 for r in parts if r["Side"] == s) for s in ("top", "bottom")}

    print(f"== {board}: DRC clean, {len(files)} Gerber/drill files, "
          f"{len(parts)} parts ({sides['top']} top, {sides['bottom']} bottom), "
          f"{len(groups)} BOM lines")
    held = [r for r in rows if r["Ref"] in ON_HOLD]
    for r in held:
        print(f"   on hold: {r['Ref']}: {ON_HOLD[r['Ref']]}")
    for val, pkg, refs in missing:
        print(f"   no LCSC yet: {val:<24} {pkg:<44} {','.join(refs)}")


if __name__ == "__main__":
    for b in (sys.argv[1:] or ["fc", "vision"]):
        make(b)
