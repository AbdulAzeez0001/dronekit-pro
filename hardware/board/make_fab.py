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

LCSC numbers come from the LCSC table below. A part with no entry is
left blank, so JLCPCB's BOM tool asks for a match on upload instead of
silently fitting a guess. See "Ordering from JLCPCB" in README.md.
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

# Value (or (value, footprint name) where one value has two packages) ->
# LCSC number. Checked 2026-11-24 against a copy of JLCPCB's in-stock
# catalogue (cdfer jlcpcb-parts-database): MPN, package, rating, and stock.
# "basic" = JLCPCB Basic part (no loading fee); the rest are Extended.
# The B2B pair isn't in that copy; C5372816 was checked on its JLCPCB page
# (261 in stock) and C5380281 on its JLCPCB part page.
LCSC = {
    "STM32F405RGT6": "C2054141",      # STM32F405RGT6TR (reel); C15742 is out of stock. 110 in stock
    "ESP32-S3-WROOM-1-N8R2": "C2913204",
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
    "LED_STRIP": "C2845362",          # HC-1.0-3PWT, JST SH 3-pin clone (genuine SM03B not in stock)
    "PWM": "C160405",                 # JST SM06B-SRSS-TB (2.3k in stock)
    "CODE_IO": "C160405",
    "1.5uH": "C3033018",              # Coilcraft XFL4020-152MEC: 4.6 A Isat, the footprint's own part
    "8MHz CL=20pF": "C2682774",       # X32258MSB4SI, 3225 4-pin, 20 pF, +/-10 ppm
    "LED_blue": "C434447",            # SZYY0402B, 0402 blue
    "BOOT": "C269272",                # C&K KMR221NGLFS, 4.2 x 2.8 mm
    "ESP_PROG": "C269272",
    "boot_mode": "C2921603",          # Copal CHS-01TA, J-lead
    # Capacitors (all Basic, Samsung)
    "100nF": "C1525",                 # CL05B104KO5NNNC, 0402 16 V X7R
    "10nF": "C15195",                 # CL05B103KB5NNNC, 0402 50 V X7R
    "20pF": "C1554",                  # 0402CG200J500NT, 0402 50 V C0G
    "1uF": "C52923",                  # CL05A105KA5NQNC, 0402 25 V X5R
    "2.2uF": "C23630",                # CL10A225KO8NNNC, 0603 16 V X5R
    "4.7uF": "C19666",                # CL10A475KO8NNNC, 0603 16 V X5R
    "10uF": "C15850",                 # CL21A106KAYNNNE, 0805 25 V X5R
    ("10uF/25V", "C_0805_2012Metric"): "C15850",
    ("10uF/25V", "C_0603_1608Metric"): "C96446",   # CL10A106MA8NRNC, 0603 25 V X5R
    "22uF/16V": "C45783",             # CL21A226MAQNNNE, 0805 25 V X5R
    "22uF/25V": "C45783",
    # Resistors, 0402 1 % (all Basic UniOhm except 374k)
    "22R": "C25092",
    "100R": "C25076",
    "1k": "C11702",
    "4.7k": "C25900",
    "5.1k": "C25905",
    "10k": "C25744",
    "100k": "C25741",
    "374k": "C25781",                 # 0402WGF3743TCE, Extended
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
            lcsc = LCSC.get((val, pkg)) or LCSC.get(val, "")
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
