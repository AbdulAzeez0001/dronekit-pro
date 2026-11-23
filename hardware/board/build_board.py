"""
DroneKit Pro - merge every circuit-as-code block into ONE board.

Runs each block script (hardware/<block>/<block>.py) in-process, collects its
parts, pins and nets, then:

  1. Replaces the per-block STM32 / ESP32-S3 stubs with ONE real U1 and ONE
     real U2 that carry the real package pin numbers:
       U1 = STM32F405RGT6 LQFP64 (defined in hardware/stm32, ST DS8626 Fig. 12)
       U2 = ESP32-S3-WROOM-1-N8R2 (41 pads, Espressif datasheet v1.8 Table 3-1)
  2. Cross-checks every stub pin against the real part: the stub's net must
     land on the real pin with the same name. Any mismatch stops the build.
  3. Merges nets by name, checks there are no duplicate reference designators,
     and runs a connectivity sanity check.
  4. Writes:
       board.net        KiCad netlist  (PCB editor: File > Import > Netlist)
       board.kicad_sch  KiCad 8 schematic, one sheet, one generated box symbol
                        per part, a net label on every connected pin and a
                        no-connect flag on every unused pin
       board.kicad_pro  KiCad project file

Then it re-reads board.kicad_sch, rebuilds connectivity purely from label and
pin coordinates, and checks it matches the merged netlist exactly.

Run:  python3 build_board.py      (from hardware/board/)
"""

import os
import re
import runpy
import sys
import uuid as _uuid
from collections import defaultdict, OrderedDict

import skidl
from skidl import Pin

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.dirname(HERE)

# Block scripts in schematic order (power first, then the brains, then the rest)
BLOCKS = [
    ("power",     "power/power.py",         "POWER: 1S/2S + USB -> buck-boost -> split 3.3 V rails"),
    ("stm32",     "stm32/stm32.py",         "FLIGHT MCU: STM32F405 + crystal, USB-C, boot, SWD"),
    ("dual-boot", "dual-boot/dual_boot.py", "DUAL-BOOT: ESP32-S3 gating, bridge UART, straps"),
    ("gyro",      "gyro/gyro.py",           "GYRO: ICM-42688-P on SPI1"),
    ("baro",      "baro/baro.py",           "BARO: SPA06-003 on I2C1"),
    ("motors",    "motors/motors.py",       "MOTORS: 4 x brushed low-side MOSFET"),
    ("camera",    "camera/camera.py",       "CAMERA: 24-pin DVP on the ESP32-S3"),
    ("elrs",      "elrs/elrs.py",           "RC RECEIVER PORT (optional ELRS add-on)"),
    ("buzzer",    "buzzer/buzzer.py",       "BUZZER: Betaflight beeper"),
    ("expansion", "expansion/expansion.py", "EXPANSION HEADERS"),
]

T = Pin.types
KICAD_TYPE = {
    T.INPUT: "input", T.OUTPUT: "output", T.BIDIR: "bidirectional",
    T.TRISTATE: "tri_state", T.PASSIVE: "passive", T.UNSPEC: "unspecified",
    T.PWRIN: "power_in", T.PWROUT: "power_out", T.OPENCOLL: "open_collector",
    T.OPENEMIT: "open_emitter", T.PULLUP: "passive", T.PULLDN: "passive",
    T.NOCONNECT: "no_connect", T.FREE: "free",
}

# ---------------------------------------------------------------------------
# ESP32-S3-WROOM-1 pads (Espressif ESP32-S3-WROOM-1/1U datasheet v1.8,
# Table 3-1 Pin Definitions). Name -> pad number.
# ---------------------------------------------------------------------------
ESP_PADS = OrderedDict([
    ("GND", 1), ("3V3", 2), ("EN", 3), ("IO4", 4), ("IO5", 5), ("IO6", 6),
    ("IO7", 7), ("IO15", 8), ("IO16", 9), ("IO17", 10), ("IO18", 11),
    ("IO8", 12), ("IO19", 13), ("IO20", 14), ("IO3", 15), ("IO46", 16),
    ("IO9", 17), ("IO10", 18), ("IO11", 19), ("IO12", 20), ("IO13", 21),
    ("IO14", 22), ("IO21", 23), ("IO47", 24), ("IO48", 25), ("IO45", 26),
    ("IO0", 27), ("IO35", 28), ("IO36", 29), ("IO37", 30), ("IO38", 31),
    ("IO39", 32), ("IO40", 33), ("IO41", 34), ("IO42", 35), ("RXD0", 36),
    ("TXD0", 37), ("IO2", 38), ("IO1", 39), ("GND_40", 40), ("EPAD", 41),
])
ESP_GND_PADS = ("GND", "GND_40", "EPAD")

# Dual-boot's STM32 stub uses signal names instead of pin names.
STM_STUB_ALIAS = {
    "MODE_SENSE": "PC13", "ESP_EN": "PB12", "BRIDGE_TX": "PA9",
    "BRIDGE_RX": "PA10", "VDD": "VDD_19", "VSS": "VSS_18",
}


class BuildError(Exception):
    pass


# ---------------------------------------------------------------------------
# 1. Run every block and collect parts
# ---------------------------------------------------------------------------
def run_block(name, rel):
    path = os.path.join(HW, rel)
    skidl.reset()
    saved = (skidl.ERC, skidl.generate_netlist)
    skidl.ERC = lambda *a, **k: None
    skidl.generate_netlist = lambda *a, **k: None
    cwd = os.getcwd()
    os.chdir(os.path.dirname(path))
    try:
        runpy.run_path(path, run_name="__main__")
    finally:
        os.chdir(cwd)
        skidl.ERC, skidl.generate_netlist = saved

    parts = []
    import builtins
    for p in builtins.default_circuit.parts:
        pins = []
        for pin in p.pins:
            net = pin.net.name if (pin.net is not None and pin.is_connected()) else None
            if net is not None and net.startswith("N$"):
                net = f"{name}_{net}"          # anonymous net: keep it block-local
            pins.append({"num": str(pin.num), "name": pin.name,
                         "type": KICAD_TYPE.get(pin.func, "unspecified"), "net": net})
        parts.append({"ref": p.ref, "name": p.name, "value": str(p.value),
                      "footprint": p.footprint or "", "pins": pins, "block": name})
    for f in ("erc", "log"):
        stem = os.path.splitext(os.path.basename(path))[0]
        for junk in (f"{stem}.{f}", f"{stem}_sklib.py"):
            jp = os.path.join(os.path.dirname(path), junk)
            if os.path.exists(jp):
                os.remove(jp)
    return parts


# ---------------------------------------------------------------------------
# 2. Merge, replacing stubs with the real U1 / U2
# ---------------------------------------------------------------------------
def merge(block_parts):
    errors = []
    real_u1 = None
    for p in block_parts["stm32"]:
        if p["ref"] == "U1":
            real_u1 = p
    if real_u1 is None or len(real_u1["pins"]) != 64:
        raise BuildError("stm32 block must define U1 with all 64 pins")
    u1_by_name = {pin["name"]: pin for pin in real_u1["pins"]}

    u2 = {"ref": "U2", "name": "ESP32-S3-WROOM-1-N8R2", "value": "ESP32-S3-WROOM-1-N8R2",
          "footprint": "RF_Module:ESP32-S3-WROOM-1", "block": "dual-boot", "pins": []}
    for nm, pad in ESP_PADS.items():
        ptype = "power_in" if nm in ("3V3",) + ESP_GND_PADS else (
            "input" if nm == "EN" else "bidirectional")
        u2["pins"].append({"num": str(pad), "name": nm, "type": ptype, "net": None})
    u2_by_name = {pin["name"]: pin for pin in u2["pins"]}

    merged = [real_u1, u2]
    for block, parts in block_parts.items():
        for p in parts:
            if p is real_u1:
                continue
            if p["ref"] == "U1":                           # STM32 stub
                for pin in p["pins"]:
                    if pin["net"] is None:
                        continue
                    real_name = STM_STUB_ALIAS.get(pin["name"], pin["name"])
                    real = u1_by_name.get(real_name)
                    if real is None:
                        errors.append(f"{block}: U1 stub pin {pin['name']} has no real pin")
                    elif real["net"] != pin["net"]:
                        errors.append(f"{block}: U1 {real_name} is on '{real['net']}' in the "
                                      f"stm32 block but '{pin['net']}' here")
                continue
            if p["ref"] == "U2" and p["name"].startswith("ESP32-S3"):   # ESP32-S3 stub
                for pin in p["pins"]:
                    if pin["net"] is None:
                        continue
                    targets = ESP_GND_PADS if pin["name"] == "GND" else (pin["name"],)
                    for t in targets:
                        real = u2_by_name.get(t)
                        if real is None:
                            errors.append(f"{block}: U2 stub pin {pin['name']} has no ESP32-S3 pad")
                        elif real["net"] not in (None, pin["net"]):
                            errors.append(f"{block}: ESP32-S3 {t} is on '{real['net']}' elsewhere "
                                          f"but '{pin['net']}' here")
                        else:
                            real["net"] = pin["net"]
                continue
            merged.append(p)

    # Unused ESP32-S3 pads become explicit no-connects
    for pin in u2["pins"]:
        if pin["net"] is None:
            pin["type"] = "no_connect"

    # Duplicate reference designators
    seen = {}
    for p in merged:
        if p["ref"] in seen:
            errors.append(f"duplicate ref {p['ref']} in {seen[p['ref']]} and {p['block']}")
        seen[p["ref"]] = p["block"]

    if errors:
        raise BuildError("\n".join(errors))
    return merged


def netmap(parts):
    nets = defaultdict(list)
    for p in parts:
        for pin in p["pins"]:
            if pin["net"]:
                nets[pin["net"]].append((p["ref"], pin["num"]))
    return nets


def sanity(parts, nets):
    problems = []
    for name, nodes in nets.items():
        if len(nodes) < 2:
            problems.append(f"net {name} has only one connection: {nodes}")
    types = {(p["ref"], pin["num"]): pin["type"] for p in parts for pin in p["pins"]}
    for name, nodes in nets.items():
        t = [types[n] for n in nodes]
        if t.count("power_out") > 1:
            problems.append(f"net {name} has {t.count('power_out')} power outputs")
    return problems


# ---------------------------------------------------------------------------
# 3. Netlist writer (KiCad "D" netlist, same shape SKiDL writes)
# ---------------------------------------------------------------------------
def q(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def write_netlist(parts, nets, path):
    out = ['(export (version "D")', '  (design (source "build_board.py") (tool "DroneKit build_board.py"))',
           "  (components"]
    for p in sorted(parts, key=lambda x: ref_key(x["ref"])):
        out.append(f"    (comp (ref {q(p['ref'])}) (value {q(p['value'])}) (footprint {q(p['footprint'])}))")
    out.append("  )")
    out.append("  (nets")
    for code, name in enumerate(sorted(nets), start=1):
        nodes = " ".join(f"(node (ref {q(r)}) (pin {q(n)}))" for r, n in sorted(nets[name]))
        out.append(f"    (net (code {code}) (name {q(name)}) {nodes})")
    out.append("  )")
    out.append(")")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")


def ref_key(ref):
    m = re.match(r"([A-Za-z#]+)(\d+)", ref)
    return (m.group(1), int(m.group(2))) if m else (ref, 0)


# ---------------------------------------------------------------------------
# 4. KiCad 8 schematic writer
# ---------------------------------------------------------------------------
G = 2.54          # grid
PIN_LEN = 2.54
FONT = "(effects (font (size 1.27 1.27)))"
FONT_HIDE = "(effects (font (size 1.27 1.27)) hide)"


_UID_NS = _uuid.UUID("6f1c2b4e-3d5a-4c7b-9e8f-0a1b2c3d4e5f")
_uid_n = [0]


def uid():
    """Deterministic UUIDs: the same inputs give the same file (clean git diffs)."""
    _uid_n[0] += 1
    return str(_uuid.uuid5(_UID_NS, str(_uid_n[0])))


def snap(v):
    return round(round(v / G) * G, 4)


def fmt(v):
    return f"{v:.4f}".rstrip("0").rstrip(".")


def sym_name(p):
    return re.sub(r"[^A-Za-z0-9_\-]", "_", p["name"])


def symbol_geometry(p):
    """Split pins left/right; return (width, height, [(pin, x, y, angle)])."""
    pins = p["pins"]
    half = (len(pins) + 1) // 2
    left, right = pins[:half], pins[half:]
    lname = max([len(x["name"]) for x in left] or [1])
    rname = max([len(x["name"]) for x in right] or [1])
    width = max(5.08, (lname + rname) * 1.0 + 5.08) if len(pins) > 2 else 5.08
    width = 2 * G * max(1, int(-(-width // (2 * G))))       # multiple of 5.08
    rows = max(len(left), len(right))
    height = (rows + 1) * G
    top = (rows - 1) * G / 2
    top = snap(top) if rows % 2 == 1 else snap(top - G / 2) + G / 2
    geo = []
    for i, pin in enumerate(left):
        geo.append((pin, -width / 2 - PIN_LEN, top - i * G, 0))
    for i, pin in enumerate(right):
        geo.append((pin, width / 2 + PIN_LEN, top - i * G, 180))
    return width, height, geo


def lib_symbol(name, p, width, height, geo):
    hide_names = len(p["pins"]) <= 2
    s = [f'    (symbol {q("dronekit:" + name)}',
         f'      (pin_names (offset 1.016){" hide" if hide_names else ""})',
         '      (exclude_from_sim no) (in_bom yes) (on_board yes)',
         f'      (property "Reference" {q(p["ref"].rstrip("0123456789"))} (at 0 {fmt(height / 2 + 1.27)} 0) {FONT})',
         f'      (property "Value" {q(name)} (at 0 {fmt(-height / 2 - 1.27)} 0) {FONT})',
         f'      (property "Footprint" "" (at 0 0 0) {FONT_HIDE})',
         f'      (property "Datasheet" "" (at 0 0 0) {FONT_HIDE})',
         f'      (property "Description" "" (at 0 0 0) {FONT_HIDE})',
         f'      (symbol {q(name + "_0_1")}',
         f'        (rectangle (start {fmt(-width / 2)} {fmt(height / 2)}) (end {fmt(width / 2)} {fmt(-height / 2)})'
         ' (stroke (width 0.254) (type default)) (fill (type background))))',
         f'      (symbol {q(name + "_1_1")}']
    for pin, x, y, ang in geo:
        s.append(f'        (pin {pin["type"]} line (at {fmt(x)} {fmt(y)} {ang}) (length {fmt(PIN_LEN)})'
                 f' (name {q(pin["name"])} {FONT}) (number {q(pin["num"])} {FONT}))')
    s.append("      )")
    s.append("    )")
    return "\n".join(s)


PWR_FLAG_LIB = """    (symbol "dronekit:PWR_FLAG" (power) (pin_numbers hide) (pin_names (offset 0) hide)
      (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "#FLG" (at 0 1.905 0) (effects (font (size 1.27 1.27)) hide))
      (property "Value" "PWR_FLAG" (at 0 3.81 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "~" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Description" "Special symbol for telling ERC where power comes from" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "PWR_FLAG_0_0" (pin power_out line (at 0 0 90) (length 0) (name "pwr" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27))))))
      (symbol "PWR_FLAG_0_1" (polyline (pts (xy 0 0) (xy 0 1.27) (xy -1.016 1.905) (xy 0 2.54) (xy 1.016 1.905) (xy 0 1.27)) (stroke (width 0) (type default)) (fill (type none))))
    )"""


def label(net, x, y, angle):
    just = "left bottom" if angle == 0 else "right bottom"
    return (f'  (label {q(net)} (at {fmt(x)} {fmt(y)} {angle}) (fields_autoplaced yes)'
            f' (effects (font (size 1.27 1.27)) (justify {just})) (uuid {q(uid())}))')


def write_schematic(parts, nets, sch_path, project):
    root = uid()
    lib, placed, extra = {}, [], []
    # symbol definitions (one per distinct name + pin set)
    for p in parts:
        base = sym_name(p)
        key = (base, tuple((x["num"], x["name"], x["type"]) for x in p["pins"]))
        if key not in lib:
            name = base if all(k[0] != base for k in lib) else f"{base}_{len(lib)}"
            w, h, geo = symbol_geometry(p)
            lib[key] = (name, w, h, geo, lib_symbol(name, p, w, h, geo))
        p["_sym"] = lib[key]

    # placement: blocks stacked vertically, parts packed in rows
    LABEL_ROOM = 30.48                    # mm each side for net labels
    sheet_w = 1500.0
    x0, y = 25.4, 25.4
    heads = []
    by_block = defaultdict(list)
    for p in parts:
        by_block[p["block"]].append(p)
    for block, _, title in BLOCKS:
        bp = sorted(by_block.get(block, []), key=lambda p: (-len(p["pins"]), ref_key(p["ref"])))
        if not bp:
            continue
        heads.append((title, x0, y))
        y += 10.16
        x, row_h = x0, 0.0
        for p in bp:
            name, w, h, geo, _ = p["_sym"]
            cell_w = w + 2 * PIN_LEN + 2 * LABEL_ROOM
            cell_h = h + 10.16
            if x + cell_w > sheet_w - 25.4 and x > x0:
                x, y = x0, y + row_h
                row_h = 0.0
            cx, cy = snap(x + cell_w / 2), snap(y + h / 2 + 5.08)
            placed.append((p, cx, cy))
            x += cell_w
            row_h = max(row_h, cell_h)
        y += row_h + 12.7
    sheet_h = max(841.0, y + 25.4)

    body = []
    for p, cx, cy in placed:
        name, w, h, geo, _ = p["_sym"]
        props = [
            f'    (property "Reference" {q(p["ref"])} (at {fmt(cx)} {fmt(cy - h / 2 - 1.27)} 0) {FONT})',
            f'    (property "Value" {q(p["value"])} (at {fmt(cx)} {fmt(cy + h / 2 + 1.27)} 0) {FONT})',
            f'    (property "Footprint" {q(p["footprint"])} (at {fmt(cx)} {fmt(cy)} 0) {FONT_HIDE})',
            f'    (property "Datasheet" "" (at {fmt(cx)} {fmt(cy)} 0) {FONT_HIDE})',
            f'    (property "Description" "" (at {fmt(cx)} {fmt(cy)} 0) {FONT_HIDE})',
            f'    (property "Block" {q(p["block"])} (at {fmt(cx)} {fmt(cy)} 0) {FONT_HIDE})',
        ]
        pins = "\n".join(f'    (pin {q(pin["num"])} (uuid {q(uid())}))' for pin, *_ in geo)
        body.append(
            f'  (symbol (lib_id {q("dronekit:" + name)}) (at {fmt(cx)} {fmt(cy)} 0) (unit 1)\n'
            f'    (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no) (uuid {q(uid())})\n'
            + "\n".join(props) + "\n" + pins + "\n"
            f'    (instances (project {q(project)} (path {q("/" + root)} (reference {q(p["ref"])}) (unit 1))))\n'
            "  )")
        own = {pin["num"]: pin for pin in p["pins"]}     # THIS part's pins (nets)
        for sym_pin, px, py, ang in geo:                  # shared symbol's positions
            pin = own[sym_pin["num"]]
            sx, sy = cx + px, cy - py
            if pin["net"]:
                extra.append(label(pin["net"], sx, sy, 180 if ang == 0 else 0))
            else:                                    # unused pin: no-connect flag
                extra.append(f'  (no_connect (at {fmt(sx)} {fmt(sy)}) (uuid {q(uid())}))')

    # PWR_FLAGs on nets that have power inputs but no power output
    types = {(p["ref"], pin["num"]): pin["type"] for p in parts for pin in p["pins"]}
    flagged = [n for n, nodes in sorted(nets.items())
               if any(types[x] == "power_in" for x in nodes)
               and not any(types[x] == "power_out" for x in nodes)]
    fx, fy = 25.4, snap(sheet_h - 20.32)
    heads.append(("POWER FLAGS (tell ERC these nets are driven)", fx, fy - 12.7))
    for i, n in enumerate(flagged):
        x = snap(fx + i * 40.64)
        body.append(
            f'  (symbol (lib_id "dronekit:PWR_FLAG") (at {fmt(x)} {fmt(fy)} 0) (unit 1)\n'
            f'    (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no) (uuid {q(uid())})\n'
            f'    (property "Reference" "#FLG{i + 1:02d}" (at {fmt(x)} {fmt(fy - 1.905)} 0) {FONT_HIDE})\n'
            f'    (property "Value" "PWR_FLAG" (at {fmt(x)} {fmt(fy - 3.81)} 0) {FONT})\n'
            f'    (property "Footprint" "" (at {fmt(x)} {fmt(fy)} 0) {FONT_HIDE})\n'
            f'    (property "Datasheet" "~" (at {fmt(x)} {fmt(fy)} 0) {FONT_HIDE})\n'
            f'    (property "Description" "" (at {fmt(x)} {fmt(fy)} 0) {FONT_HIDE})\n'
            f'    (pin "1" (uuid {q(uid())}))\n'
            f'    (instances (project {q(project)} (path {q("/" + root)} (reference "#FLG{i + 1:02d}") (unit 1))))\n'
            "  )")
        extra.append(label(n, x, fy, 0))

    texts = [f'  (text {q(t)} (exclude_from_sim no) (at {fmt(x)} {fmt(y)} 0)'
             f' (effects (font (size 3.81 3.81) (thickness 0.762) bold) (justify left bottom)) (uuid {q(uid())}))'
             for t, x, y in heads]

    doc = [
        '(kicad_sch (version 20231120) (generator "eeschema") (generator_version "8.0")',
        f'  (uuid {q(root)})',
        f'  (paper "User" {fmt(sheet_w)} {fmt(sheet_h)})',
        '  (title_block (title "DroneKit Pro flight controller") (company "DroneKit Pro")'
        ' (comment 1 "Generated by hardware/board/build_board.py from the circuit-as-code blocks - do not hand-edit"))',
        "  (lib_symbols",
        "\n".join(v[4] for v in lib.values()),
        PWR_FLAG_LIB,
        "  )",
        "\n".join(texts),
        "\n".join(body),
        "\n".join(extra),
        '  (sheet_instances (path "/" (page "1")))',
        ")",
    ]
    with open(sch_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(doc) + "\n")
    return placed, flagged


def write_project(path, name):
    import json
    pro = {"meta": {"filename": f"{name}.kicad_pro", "version": 1},
           "sheets": [], "text_variables": {}}
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(pro, f, indent=2)
        f.write("\n")


# ---------------------------------------------------------------------------
# 5. Independent check: rebuild connectivity from the schematic file itself
# ---------------------------------------------------------------------------
def verify_schematic(sch_path, nets):
    txt = open(sch_path, encoding="utf-8").read()
    # lib symbol pin positions
    libpins = defaultdict(list)
    for m in re.finditer(r'\(symbol "dronekit:([^"]+)"(.*?)\n    \)', txt, re.S):
        for pm in re.finditer(r'\(pin \w+ line \(at ([-\d.]+) ([-\d.]+) \d+\).*?\(number "([^"]+)"', m.group(2)):
            libpins[m.group(1)].append((float(pm.group(1)), float(pm.group(2)), pm.group(3)))
    # placed symbols
    point_pin = {}
    for m in re.finditer(r'\(symbol \(lib_id "dronekit:([^"]+)"\) \(at ([-\d.]+) ([-\d.]+) 0\)'
                         r'.*?\(property "Reference" "([^"]+)"', txt, re.S):
        lib_name, cx, cy, ref = m.group(1), float(m.group(2)), float(m.group(3)), m.group(4)
        if ref.startswith("#"):
            continue
        for px, py, num in libpins[lib_name]:
            point_pin[(round(cx + px, 3), round(cy - py, 3))] = (ref, num)
    got = defaultdict(list)
    for m in re.finditer(r'\(label "([^"]+)" \(at ([-\d.]+) ([-\d.]+) \d+\)', txt):
        key = (round(float(m.group(2)), 3), round(float(m.group(3)), 3))
        if key in point_pin:
            got[m.group(1)].append(point_pin[key])
    want = {n: sorted(v) for n, v in nets.items()}
    got = {n: sorted(v) for n, v in got.items()}
    return want == got, want, got


# ---------------------------------------------------------------------------
def main():
    block_parts = OrderedDict()
    for name, rel, _ in BLOCKS:
        block_parts[name] = run_block(name, rel)
        print(f"  {name:10} {len(block_parts[name]):3} parts")
    parts = merge(block_parts)
    nets = netmap(parts)
    problems = sanity(parts, nets)
    for p in problems:
        print("  CHECK:", p)
    if problems:
        raise BuildError("connectivity check failed")

    os.chdir(HERE)
    write_netlist(parts, nets, "board.net")
    placed, flagged = write_schematic(parts, nets, "board.kicad_sch", "board")
    write_project("board.kicad_pro", "board")
    ok, want, got = verify_schematic("board.kicad_sch", nets)
    if not ok:
        for n in sorted(set(want) | set(got)):
            if want.get(n) != got.get(n):
                print("  MISMATCH", n, want.get(n), got.get(n))
        raise BuildError("schematic connectivity does not match the netlist")

    npins = sum(len(p["pins"]) for p in parts)
    nc = sum(1 for p in parts for pin in p["pins"] if not pin["net"])
    print(f">>> {len(parts)} parts, {len(nets)} nets, {npins} pins ({nc} unconnected)")
    print(f">>> power flags on: {', '.join(flagged) or '-'}")
    print(">>> wrote board.net, board.kicad_sch, board.kicad_pro")
    print(">>> schematic connectivity re-read from file: matches the netlist")


if __name__ == "__main__":
    try:
        main()
    except BuildError as e:
        print("BUILD FAILED:\n" + str(e))
        sys.exit(1)
