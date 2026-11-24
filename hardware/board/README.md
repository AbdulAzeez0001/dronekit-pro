# Board — the blocks merged, then split into two stacked boards

`build_board.py` merges all ten circuit-as-code blocks into one system
schematic. Then it splits that into the two physical boards, **fc** (bottom)
and **vision** (top); see "Two boards" below. `build_pcb.py` starts each
board's PCB.

| File | What it is | Made by |
|---|---|---|
| `board.kicad_sch`, `board.net` | the whole system on one sheet: 155 parts, 116 nets. Reference only, no PCB | `build_board.py` |
| `fc.kicad_pro` / `.kicad_sch` / `.net` | flight-controller board: 105 parts incl. header J200 | `build_board.py` |
| `vision.kicad_pro` / `.kicad_sch` / `.net` | vision board: 52 parts incl. socket J201 | `build_board.py` |
| `fc.kicad_pcb`, `vision.kicad_pcb` | 4-layer 32 × 30 mm boards, both placed and routed | `build_pcb.py`, then the scripts below |
| `place_fc.py`, `place_vision.py` | each board's part placement (fixed spots + anchors) | by hand |
| `placer.py` | the placement engine both use | by hand |
| `route_setup.py`, `autoroute.py`, `fanout.py`, `handroute.py` | routing: net classes and pours, Freerouting, ground stitching, the rip-up router for what's left | by hand |
| `preroute_power.py`, `power_pour.py` | fc only: the battery and motor paths routed wide before everything else, then widened with pours and extra vias | by hand |
| `renders/` | KiCad 3D views of both sides of both boards | `kicad-cli pcb render` |
| `dronekit.pretty/` | custom footprints KiCad doesn't ship (TPS63070, M1.4 hole, wire pads, board-edge ESP32-S3) | `make_footprints.py` |
| `fp-lib-table` | points KiCad at `dronekit.pretty` (shared by both projects) | by hand |

**The schematics and netlists are generated, so don't hand-edit them.** Change the
block `.py` files and re-run the build. Rebuilds are deterministic: the same
blocks give byte-identical files, so git diffs show only real changes.

## Build

```
pip install skidl --break-system-packages
cd hardware/board
python3 build_board.py
```

Expected output ends with:

```
>>> 155 parts, 116 nets, 526 pins (28 unconnected)
>>> power flags on: GND, VBAT
>>> wrote board.net, board.kicad_sch, board.kicad_pro (whole system)
>>> schematic connectivity re-read from file: matches the netlist
>>> split: 17 nets cross on J200/J201: +3V3_ESP, +3V3_SYS, +3V8, ...
>>> fc    : 105 parts, 76 nets, power flags on GND, VBAT; wrote fc.net/.kicad_sch, re-read OK
>>> vision: 52 parts, 57 nets, power flags on +3V8, GND; wrote vision.net/.kicad_sch, re-read OK
```

## What the build does

1. **Runs every block script** in-process and collects its parts, pins and
   nets. It doesn't rewrite the block `.net` files.
2. **Replaces the stubs with one real STM32 (U1) and one real ESP32-S3
   (U2).**
   - Several blocks carry their own `U1`/`U2` stub with local pin numbers.
     The build keeps:
     - `U1` from `hardware/stm32`: STM32F405RGT6 LQFP64, with pins per ST
       DS8626, Figure 12.
     - A real `U2`: ESP32-S3-WROOM-1-N8R2, 41 pads per the Espressif
       datasheet v1.8, Table 3-1.
   - Every stub pin is checked against the real part. Its net must already
     be on the real pin of the same name, so a block wired to the wrong pin
     stops the build.
3. **Checks the result:**
   - no duplicate reference designators;
   - no net with a single connection;
   - no net with two power outputs.
4. **Writes the schematic:**
   - Each part gets a simple generated box symbol, embedded in the file.
   - Every connected pin gets a net label; parts connect by label name.
   - Every unused pin gets a no-connect flag.
   - Parts are grouped by block under a heading.
   - `PWR_FLAG`s go on GND and VBAT: nets with power inputs but no power
     output, so KiCad's ERC knows they're driven.
5. **Re-reads `board.kicad_sch`** and rebuilds the connectivity purely from
   pin and label coordinates, then confirms it matches the netlist exactly.
6. **Splits into fc and vision** (`BOARD_OF_BLOCK`, `BOARD_EXCEPTIONS`),
   adds J200/J201 with `B2B_PINOUT`, and checks the split:
   - every net with parts on both boards has a J200/J201 pin;
   - J200/J201 carry no net that doesn't need to cross.

   Then it writes, checks and re-reads each board's schematic as in steps
   3–5. `fc.kicad_pro` and `vision.kicad_pro` are written only if missing,
   so the design rules `build_pcb.py` puts in them survive a rebuild.

## Unconnected pins (all 28 are intentional)

| Part | Unused pins | Why |
|---|---|---|
| U1 STM32 | PC14, PC15, PC0, PC2, PC3, PA0, PA1, PC5, PB13–15, PA15, PC10–12, PD2, PB3 | spare: ADC pins + the SPI3 bank (see the pin map) |
| U2 ESP32-S3 | IO3, IO35–37 | IO3 is a strap (left floating on purpose); IO35–37 are spare on the N8R2 |
| U10 TPS63070 | FB2 | VSEL unused (single output voltage) |
| U11 RT9013 | NC | not connected inside the part |
| J90 USB-C | SBU1, SBU2 | not used by USB 2.0 |
| J30 camera FPC | Y0, Y1, NC | camera's 2 low data bits unused (8-bit mode) |

The ESP32-S3's programming pins are wired:

- **Native USB (IO19/IO20)** reaches the USB-C port through the TS3USB221A
  switch in Mode B.
- **UART0 (RXD0/TXD0)** goes to the J1 recovery pads.

See `hardware/stm32/stm32-design.md`.

## KiCad checks (KiCad 10.0.8, 2026-11-23)

- **ERC** on `board.kicad_sch`, `fc.kicad_sch` and `vision.kicad_sch`:
  0 errors. The only warnings say the `dronekit` symbol library isn't in
  KiCad's library table. The symbols are embedded in the schematics, so
  that's harmless.
- **Netlist:** KiCad's own netlist of `board.kicad_sch` has the same 116
  connected nets as `board.net`, pin for pin, plus one single-pin net for
  each of the 28 unused pins.
- **DRC** on `fc.kicad_pcb` and `vision.kicad_pcb`, with the schematic
  parity check: 0 violations and 0 parity issues on each. The unconnected
  items (fc 274, vision 141) are the ratsnest; nothing is routed yet.

```
"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe" sch erc fc.kicad_sch
"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe" pcb drc --schematic-parity fc.kicad_pcb
```
(same for `vision`).

## The PCB (`build_pcb.py`)

```
cd hardware/board
python make_footprints.py                                   # custom footprints
"C:\Program Files\KiCad\10.0\bin\python.exe" build_pcb.py fc       # needs KiCad's pcbnew
"C:\Program Files\KiCad\10.0\bin\python.exe" build_pcb.py vision
```

Both boards get the same:

- **Outline:** 32 × 30 mm with a 2 mm corner radius, centred at (150, 100)
  on the page. It matches `hardware/mechanical/fc_pcb_outline.dxf`; +X is the
  front, on the camera side.
- **Holes:** H1–H4, M1.4 (1.6 mm, not plated), on a 25.5 mm square. Each has
  a 3.6 mm keep-out on both sides for the standoffs.
- **Stackup:** 4 copper layers. fc is 1.6 mm thick and vision 1.0 mm
  (lighter; it carries no motor current). The plan is In1 = GND and
  In2 = power; neither plane is poured yet.
- **Rules:** set for JLCPCB's standard 4-layer process. Clearance and the
  smallest track are 0.1 mm, the default track is 0.15 mm, and vias are
  0.45 mm with a 0.2 mm drill. They're stored in `<board>.kicad_pro`.
- **Parts:** all are loaded with their nets and linked to their schematic
  symbols. The board-to-board pair is placed and locked; every other part is
  parked right of the board, one column per block.

**Re-running `build_pcb.py` overwrites `<board>.kicad_pcb`, including any
placement.** Once placement starts in KiCad, change the schematic with
`build_board.py`, then use **Tools > Update PCB from Schematic**.

Footprints that changed so the schematic fits KiCad 10's libraries:

- **TPS63070 (U10):** `dronekit:TI_RNM0015A_VQFN-HR-15_2.5x3mm_P0.5mm`,
  drawn from TI's land pattern (SLVSC58B, page 40). Re-check it against
  TI's current drawing before ordering.
- **TS3USB221A (U92):** KiCad's `Package_DFN_QFN:Texas_UQFN-10_1.5x2mm_P0.5mm`,
  which is TI's RSE0010A.
- **Inductor (L10):** `Inductor_SMD:L_Coilcraft_XxL4020`, the XFL/XAL4020
  footprint.
- **USB-C shield (J90):** the pad is named `SH` in KiCad's HRO footprint,
  not `S1`.

- **Wire pads** (battery J10, motors J40–J43, receiver J60, buzzer J120,
  SWD J91, ESP UART0 J1): plain SMD pads from `make_footprints.py`, with no
  paste because they're hand-soldered. They replace the through-hole
  pin-header placeholders, whose pins blocked both sides of the board.
  - Battery: 2.5 × 3.5 mm pads at 3.5 mm.
  - Motors and buzzer: 1.3 × 2.0 mm pads at 2.0 mm.
  - The rest: 1.0 × 1.8 mm pads at 1.5 mm.
- **Push buttons** SW90 (STM32 BOOT) and SW2 (ESP program): C&K KMR2,
  4.2 × 2.8 mm (`Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2`), instead of
  the 6.2 × 6.2 mm SKQG. Same pin numbers.
- **Boot-mode switch** SW1: a 1-position slide switch you flip from above,
  the Copal CHS-01A (`SW_DIP_SPSTx01_Slide_Copal_CHS-01A_W5.08mm_P1.27mm_JPin`,
  7.3 × 3.3 mm). It replaces the side-lever PCM12 (8.9 × 5.9 mm), which
  had no edge space left on the vision board. It's the same 2-pin switch.
- **ESP32-S3 module (U2):** `dronekit:ESP32-S3-WROOM-1_BoardEdge`, made
  from KiCad's own footprint by `make_footprints.py`.
  - **Courtyard:** the module body only. KiCad's covers the 48 × 41 mm
    antenna clearance area, so every nearby part showed as a courtyard
    overlap.
  - **Keep-out:** trimmed to 21.8 mm across, so it ends just short of the
    two rear mounting holes. It still bans copper and parts on every layer
    beside the antenna.

Still to check: the ICM-42688-P footprint
`LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y` against the datasheet land
pattern.

## Two boards (decided 2026-11-23)

The parts don't fit on one 32 × 30 mm board (see the area table below), so
the electronics are two boards with the same outline. They stack on the same
four M1.4 holes and are joined by one connector pair.

| Board | Where | What's on it | Parts' area |
|---|---|---|---|
| **fc** | bottom, 1.6 mm | power (battery, buck-boost, RT9013), STM32 + crystal, USB-C + ESD + USB switch, BOOT button, SWD, gyro, baro, motor drivers, buzzer, receiver port, the STM32's sensor-I²C and UART3 ports, the STM32 BOOT0/NRST parts | 1,150 mm² |
| **vision** | top, 1.0 mm | ESP32-S3-WROOM-1 + its AP7361C LDO, camera FPC and camera LDOs, boot-mode switch, ESP program button and UART0 pads, PWM and LED-strip ports, the ESP32-S3's I²C and IO ports | 1,206 mm² |

Each board has about 1,840 mm² on its two sides, so each is about 63 %
full. That's dense but buildable on 4 layers with parts on both sides.
(The areas are from before the smaller buttons and SMD wire pads; both
boards are a little emptier now.) If the vision board gets tight, these
swaps free the most room:

- the PCM12 slide switch SW1 for a smaller one;
- the SOT-223 LDO (U12) for an SOT-89 one;
- on fc, the four SMA flyback diodes for SOD-123FL ones.

## fc placement (`place_fc.py`, 2026-11-23)

![fc top](renders/fc_top.png) ![fc bottom](renders/fc_bottom.png)

(`renders/`: KiCad 3D views; the bottom view is seen from below, so it's
mirrored.)

```
"C:\Program Files\KiCad\10.0\bin\python.exe" build_pcb.py fc   # fresh board
"C:\Program Files\KiCad\10.0\bin\python.exe" place_fc.py        # place every part
```

The script places every part and is the record of why each one is where it
is. It refuses any courtyard overlap, keeps parts clear of the rounded
corners and the copper-to-edge rule, and lists every part it had to put
more than 4 mm from the pin it serves.

**Top**, which ends up under the vision board:

- **STM32:** in the middle, turned so that its USB, ESP32-S3, PWM and
  LED-strip pins (33–48) face J200.
- **Decoupling caps:** each at its supply pin.
- **Clock and boot:** the 8 MHz crystal at pins 5–6; the BOOT0, BOOT1, NRST
  and status-LED parts at their pins.
- **USB:** USB-C on the rear edge. The USBLC6 ESD chip sits between it and
  the TS3USB221A switch. The switch sits left of the band between the STM32
  and J200, next to J200's USB pins (7/8), so the band stays free for the
  STM32's escape wires. The two VCAP caps sit at the sides of that band for
  the same reason.
- **Front edge:** the sensor-I²C (J130) and UART3 (J131) JST-SH ports, with
  their series resistors.
- **Rear-left corner:** the RT9013 3.3 V LDO and the SPA06 baro.

**Bottom.** It's the only fc side you can reach with the vision board on,
so every wire pad is here.

- **Motors:** the four motor pad pairs sit at the corners, beside the
  mounting holes, where the wires come up from the pods. Each has its SS34
  diode and AO3400A FET right beside it:
  - the front diodes stand upright;
  - the rear ones lie flat, to clear the USB-C shell pins.
- **Buck-boost (left edge):** the TPS63070, with its inductor on the side
  of its L1/L2 pins, its input caps on the VIN side and its output caps on
  the VOUT side. It's about 9 mm from the gyro.
- **Battery input:** the battery pads, with the AO3401A reverse-polarity
  FET and the USB diode next to them.
- **Gyro:** the ICM-42688-P near the centre, next to the STM32's SPI1 pins,
  with its caps tight around it.
- **Other wire pads:** SWD, receiver and buzzer, with the buzzer's driver
  beside its pads.
- **BOOT button (KMR2):** at the front, pressable from below.

**Checks:** KiCad DRC reports 0 errors and 0 schematic-parity issues. The 45
warnings are all silkscreen: text clipped at the edge or overlapping a
neighbour's outline. Only the parts a builder solders or plugs into keep
their reference on the silkscreen; every other reference stays on the fab
layer. Routing: see "fc routing" below.

**Gyro orientation:** U80 sits at rotation 0 on the bottom, chip top facing
down, pin 1 at the rear-right corner seen from below. That puts the chip's
+X forward, +Y right and +Z down: a 180° roll flip from Betaflight's frame,
so `gyro_1_sensor_align = CW180FLIP`
(`firmware/betaflight/cli-defaults.txt`). This assumes InvenSense's usual
axis figure (pin 1 top-left, +X right, +Y up); TDK's datasheet could not be
fetched to confirm it. Bench-check the three axes in the Configurator before
the first flight (steps in that file).

## fc routing (2026-11-23, power paths redone 2026-11-24)

```
"C:\Program Files\KiCad.0in\python.exe" route_setup.py fc            # classes, pours, edge keep-out
"C:\Program Files\KiCad.0in\python.exe" preroute_power.py fc         # battery and motor paths first, wide
"C:\Program Files\KiCad.0in\python.exe" autoroute.py fc start --inner2  # Freerouting, detached
"C:\Program Files\KiCad.0in\python.exe" autoroute.py fc finish         # once .routing/fc.ses exists
"C:\Program Files\KiCad.0in\python.exe" fanout.py fc                   # a GND via in every floating ground island
"C:\Program Files\KiCad.0in\python.exe" handroute.py fc                # rip-up router for what's left
"C:\Program Files\KiCad.0in\python.exe" power_pour.py fc               # pours and extra vias along the power paths
```

**Result:** KiCad DRC reports 0 errors, 0 unconnected and 0 schematic-parity
issues. The 45 silkscreen warnings are the same as before. There are also 3
"dangling track" warnings: short stubs that the I2C clock line runs through,
so removing them breaks it. The board has 2852 track segments and 312 vias,
about 1.6 m of track: 736 mm on F.Cu, 417 mm on B.Cu and 450 mm on In2.Cu.
In1.Cu is a solid GND plane. In2.Cu is the +3V3_SYS pour, which signals also
cross where they have to.

### Power paths

The motors run straight off the battery: about 2.5 A per motor at full
throttle, about 10 A in all at the battery pads. The first routing left the
power nets the 0.8 mm the signals left free. One side's battery feed ran on
In2.Cu (0.5 oz, about 0.9 A at 0.8 mm) through a single via, which would have
overheated.

The power nets are now routed **first**, on the empty board
(`preroute_power.py`):

- **Layers and vias:** they use F.Cu and B.Cu only, since In2 is priced out.
  A layer change costs as much as 10 mm of track, and a path that needs more
  than 3 vias drops to the next narrower width.
- **Widths:**
  - the battery to J43: 2.0 mm;
  - then on to J42: 1.6 mm. That path runs down the right edge and around
    the bottom, and the other two motors branch off it (see the table
    below);
  - each motor's own branch and its negative to the FET: 1.0 mm (2.5 A);
  - the reverse-polarity FET and the buck-boost input: 0.8 mm.
- **Wider on the first try:** 2.5 mm everywhere left Freerouting 26
  connections short.

After the signals are routed, `power_pour.py` lays a copper pour along every
power track on F.Cu and B.Cu. The pours are wider than the track wherever
there is room. It also adds up to 6 more 0.6 / 0.3 mm vias around every power
via (17 in all), so no layer change carries the whole current through one
via.

The battery feed is a chain, not a star. From the battery pad (J10) it
runs down the right side to J43, down the right edge to J41, along the bottom
to J40 and up the left side to J42. Each stretch carries the motors still
ahead of it. The right edge, which carries three motors, has a second path
beside it: a 1.2 mm F.Cu track (19.5 mm) from the J43 junction to the J41
junction. It joins B.Cu through 2 vias at the top end and 3 at the bottom, and
takes about 2.9 A of the 7.5 A (the split follows the two paths' copper
resistance). A separate feed from the battery to the left motors doesn't fit:
the buck-boost on B.Cu and the parts on F.Cu leave no outer-layer path across
the top, even with signals ripped up, only one that runs 13 mm on In2. The copper width along each stretch is the track, or the pour
around it where that is wider (IPC-2221 temperature rise, all four motors at
2.5 A):

| Stretch | Carries | Narrowest copper | Rise, 1 oz outer | Rise, 2 oz outer |
|---|---|---|---|---|
| J10 pad to the J43 junction (B.Cu) | 10 A | 3.2 mm | about 38 °C | about 12 °C |
| right edge, J43 to J41 (B.Cu) | 4.6 A of the 7.5 A | 1.6 mm | about 20 °C | about 7 °C |
| right edge, parallel path (F.Cu) | 2.9 A of the 7.5 A | 1.1 mm | about 13 °C | about 4 °C |
| bottom, J41 to J40 (B.Cu) | 5 A | 1.77 mm | about 21 °C | about 7 °C |
| left side, J40 to J42 (F.Cu) | 2.5 A | 1.5 mm | about 6 °C | about 2 °C |
| each motor's negative, M1–M4_NEG | 2.5 A | 0.9 mm or more | about 13 °C | about 4 °C |

At JLCPCB's default 1 oz, every stretch but the first stays at about a
20 °C rise or less with all four motors at full throttle. The hottest is now
the 10 A stretch from the battery pad (about 38 °C). **2 oz outer copper**
brings every stretch to about 12 °C or less. IPC-2221 is cautious for
stretches this short, which shed heat into the pads and pours around them,
and 0802-size brushed motors usually draw less than 2.5 A.

**Fixes after the power pre-route:**

- **R15 battery-sense line:** Freerouting gave it the full VBAT_RAW width
  (0.8 mm), in a loop around the top of the STM32 that walled off the crystal
  and I2C pins. It carries no current, so it was ripped up and re-routed
  thin.
- **C16** (buck-boost VAUX cap): `place_fc.py` now turns it 180° (`TURN`),
  so its VAUX pad faces U10.3.
- **U10's VBAT feed:** it ran 0.15 mm under the BB_EN pin, so BB_EN could
  not get out. The feed was re-routed at 0.8 mm from the battery side.
- **Swapped rip-ups:** I2C1_SDA vs M4_PWM, and BEEPER vs LED0_K, kept
  ripping each other up. Each pair was closed by routing one with the other
  held fixed.
- **Right-edge parallel path** (added after the rest was routed): it ripped
  up BRIDGE_TX, ESP_USB_DP, I2C1_SCL, STM_BOOT0 and some GND stitching, and
  `handroute.py` re-routed them (LED_STRIP too, ripped on the way). The
  second via at its top end has a 1.45 mm B.Cu stub to the trunk: no spot
  near there has the net's pour on both layers.
- **Cleanup:** duplicate and overlapping copper left over from the
  hand-router rounds was removed, each piece only if DRC stayed clean
  without it.

The placement still rebuilds exactly (`build_pcb.py fc` + `place_fc.py`). The
routing doesn't: Freerouting isn't deterministic, and the fixes above were
made on the routed board.

**How it got there:**

- **Freerouting:** with the power paths routed first, it leaves 4
  connections. It runs to pass 999 and ignores its pass and time limits.
- **`fanout.py`:** puts a GND via in each ground-fill island on F.Cu and B.Cu
  that has no other way down to In1.
- **`handroute.py`:** a grid maze router (0.05 mm grid, F.Cu / In2.Cu / B.Cu)
  for the rest.
  - It can rip up and re-route other nets' wires.
  - The battery, motor, supply and USB-in nets are never ripped up.
  - Each round runs in a fresh process, it keeps the best round, and it
    saves every round in `.routing/`.
- **The last few connections were closed by hand.** The fixes are recorded
  in the build scripts, so a rebuild keeps them.

**What it took:**

- **J200 pinout:** reordered to match the STM32's pins (see "Two boards").
  With the first pinout every U1-J200 wire crossed all the others, and the
  best result was 24 unconnected.
- **C99** (100 nF on VBAT, pin 1): `place_fc.py` had it anchored to pin 13,
  which put it in the densest corner, over the buck-boost inductor. It is now
  at pin 1.
- **C71** (the baro's cap): `place_fc.py` turns it 180° in place after the
  anchor search (`TURN`), so its pads face U70's matching pins. Otherwise
  the two wires have to cross, and no via fits there because J42's pad is
  underneath.
- **Placement is now repeatable.** `placer.py` used to place the parts with
  no anchor in the board file's footprint order, which follows the random
  footprint IDs of each fresh build. It now orders them by pad count, then
  reference. R60/R61 are pinned at the spots fc was routed with. Two fresh
  `build_pcb.py fc` + `place_fc.py` runs give exactly the routed board's
  part positions.
- **USBLC6 (U91):** pins 3/4 (and 1/6) are one I/O line, joined inside the
  chip so the signal flows straight through it. `build_pcb.py` writes them
  as a jumper pad group into the footprint, so DRC counts that connection.
- **Datasheet pin check (2026-11-24):**
  - **AP7361C-33E (vision U12):** Diodes DS37274 (Oct 2020) lists two
    SOT-223 pinouts. Suffix **E** (`AP7361C-33E-13`) is pin 1 IN, pin 2
    GND (and the tab), pin 3 OUT. That matches the footprint: pin 1 is
    +3V8, pins 2 and tab are GND, pin 3 is +3V3_ESP. Suffix **ER** (SOT223R)
    is reversed (1 GND, 2 OUT, 3 IN). **Order -33E-13, not -33ER-13**; the
    ER part would short +3V8 to ground.
  - **USBLC6-2SC6 (fc U91):** pin 1 I/O1, 2 GND, 3 I/O2, 4 I/O2, 5 VBUS,
    6 I/O1. That matches the board: 1/6 are USB_DP, 3/4 are USB_DN, 2 is
    GND and 5 is VBUS. ST's PDF could not be fetched here, so this was
    checked against KiCad's own `Power_Protection` symbol, which cites it.
- **Solid pour connections:** the GND and +3V3 pins of J200 and the USB-C
  shell pins join their pours solid. On the 1.27 mm grid the neighbouring
  tracks leave too little room for thermal spokes.

**Before ordering:**

- **Look over the routing in KiCad.** It is machine-routed.
- **Small parts.** Some tracks are 0.12 mm and some ground pins reach their
  plane through a short stub. That is inside JLCPCB's 4-layer limits but
  tighter than hand routing would be.
- **USB pairs.** They are routed at 0.2 mm but not length-matched. That is
  fine at full speed (12 Mb/s).


## vision placement (`place_vision.py`, 2026-11-23)

![vision top](renders/vision_top.png) ![vision bottom](renders/vision_bottom.png)

```
"C:\Program Files\KiCad\10.0\bin\python.exe" build_pcb.py vision   # fresh board
"C:\Program Files\KiCad\10.0\bin\python.exe" place_vision.py        # place every part
```

The fc and vision scripts share one placement engine, `placer.py`, with
the same rules (see "fc placement").

**Top** (under the battery):

- **ESP32-S3-WROOM-1:** turned so its antenna is at the rear edge and hangs
  1.4 mm past it. That puts:
  - the camera pins toward the front edge;
  - the USB, EN and power pins toward J201;
  - IO38–40, UART0 and the bridge pins toward the left edge.
- **Front edge:** the ESP I²C (J134) and ESP IO (J135) JST ports.
- **Left edge, reachable from above:** the boot-mode switch SW1, the ESP
  program button SW2 and the UART0 pads J1.

**Bottom** (faces the fc board's top):

- **Front edge:** the camera FPC J30, centred on the camera pins, with the
  2.8 V and 1.2 V camera LDOs and their caps beside it.
- **Left edge:** the PWM (J133) and LED-strip (J132) JST ports.
- **ESP supply:** the AP7361C LDO under the module.

**Antenna:** the copper keep-out covers the rear strip (x < −11.4 mm)
between the two rear holes, on every layer. Use nylon screws at H1/H4.
Check the cage clears the antenna, which ends 1.4 mm past the board's rear
edge (x = −17.4 mm).

**Heights between the boards.** The header + socket gap is 5.5 mm (set by the spacers, see below).

| vision bottom | over fc top | total |
|---|---|---|
| J30 FPC, 2.0 mm | J130/J131 JST, 2.95 mm | 4.95 mm |
| J133/J132 JST, 2.95 mm | crystal, RT9013, baro, caps, ≤ 1.2 mm | ≤ 4.15 mm |
| nothing | USB-C, 3.3 mm | — |
| AP7361C, 1.8 mm | STM32, 1.6 mm | 3.4 mm |

**The FPC stack (4.95 mm) is the tightest.** Pick a header + socket pair
that gives at least 5.5 mm between the boards.

**Chosen pair (2026-11-24), same footprints, so no re-routing:**

| Ref | Part | Checked |
|---|---|---|
| J201 (socket, vision underside) | HCTL PM127-2-12-Z-4.3-G0, JLCPCB/LCSC C5380281: 2 × 12, 1.27 mm, through-hole, 4.3 mm insulator | JLCPCB part page |
| J200 (header, fc top) | HCTL PZ127-2-12-Z, JLCPCB/LCSC C5372816: 2 × 12, 1.27 mm, through-hole, 1.0 mm insulator, 3.8 mm mating pin, 2.4 mm tail | JLCPCB part page (261 in stock, $0.28) |

JLCPCB has no 1.27 mm 2 × 12 header with a 1.5 mm insulator. With this one
fully seated, the gap is 4.3 + 1.0 = 5.3 mm, which leaves only 0.35 mm over
the FPC stack. So **the spacers on H1–H4 are 5.5 mm**:

- the gap is 5.5 mm, leaving 0.55 mm over the FPC stack;
- the header pins sit 0.2 mm short of fully seated, so 3.6 of the 3.8 mm
  mating length is in the socket;
- the header's 2.4 mm tail pokes about 0.8 mm out of fc's underside (1.6 mm
  board), so trim it flush if it gets in the way of the frame.

Both parts are from HCTL, so they're meant to mate.

**Camera ribbon:** the FPC is now on the underside. Choose a top- or
bottom-contact 24-pin connector so its contacts face the ribbon's exposed
side.

**Checks:** KiCad DRC reports 0 errors and 0 schematic-parity issues; the
24 warnings are all silkscreen. Routing: see "vision routing" below.

**Connector:** a 2 × 12, 1.27 mm through-hole pair. J200 is a male header on
top of fc. It plugs into J201, a female socket on the underside of vision.
`build_pcb.py` places both so pin N is at the same XY on both boards, and
checks it.

The pinout (`B2B_PINOUT` in `build_board.py`) carries 17 nets:

| Pins | Net | Why it crosses |
|---|---|---|
| 1, 2, 6, 16, 19, 20 | GND | |
| 3, 4, 5 | +3V8 | feeds the vision board's AP7361C (ESP32-S3 + camera, about 0.5 A peak) |
| 7, 8 | ESP_USB_DP/DN | USB-C → TS3USB221A (fc) → ESP32-S3 native USB |
| 9, 10 | ESP_EN, MODE_SENSE | STM32 gates the ESP32-S3; the mode switch steers USB |
| 11–14 | PWM1–4 | STM32 outputs → PWM port J133 |
| 15 | LED_STRIP | STM32 output → LED-strip port J132 |
| 17, 18 | BRIDGE_TX/RX | STM32 USART1 ↔ ESP32-S3 |
| 21, 22 | STM_BOOT0, STM_NRST | the ESP32-S3 can flash the STM32 |
| 23 | +3V3_SYS | the boot-mode switch's pull-up |
| 24 | +3V3_ESP | back down to the fc sensor-I²C port J130 |

The signal pins run left to right in the same order as the STM32 pins they
come from (pin 33 ESP_EN, 37–40 PWM1–4, 41 LED_STRIP, 42/43 USART1), so on
fc the wires between U1 and J200 don't cross. The first pinout had them in
reverse order, and fc couldn't be routed with it.

**Stack height.** The gap between the boards is 5.5 mm (the spacers; see "Chosen pair"),
so keep fc's top-side parts under
about 4.5 mm (USB-C is 3.3 mm) and only small passives on vision's
underside. Above fc, the stack needs roughly gap + 1.0 mm board + 3.1 mm
ESP32-S3 module = 9.6 mm, against the 4.4 mm the cage leaves under the
battery now. **The cage's `fc_clear` has to grow by about 5.2 mm** (see
`hardware/mechanical/README.md`).

**Weight:** about +3 g: the second board, the connector pair and spacers,
and a taller cage. On a 300 mAh pack the quad goes from about 43 g to
46 g, and thrust/weight from about 2.0 to 1.9 (`simulation/thrust-weight.md`).

### Area of the parts by block

Courtyard area of the parts as chosen, in mm². U2 is counted as its module
body only (18 × 25.5 mm), without the antenna keep-out:

| Block | mm² | Biggest items |
|---|---|---|
| dual-boot | 602 | ESP32-S3-WROOM-1 (459), 2 × SKQG switches |
| stm32 | 442 | LQFP-64 (182), USB-C (102), SKQG BOOT switch, SWD header |
| expansion | 380 | 6 JST-SH side-entry connectors |
| power | 239 | SOT-223 LDO (65), XFL4020 inductor, battery header |
| motors | 234 | 4 × SMA diodes (102), 4 × SOT-23 FETs |
| camera | 196 | Hirose FH12 24-pin FPC (145) |
| buzzer, receiver, gyro, baro | 114 | |
| **total** | **2208** | |

One board's two sides, less the four hole keep-outs, give about
**1,840 mm²**. Parts usually need about twice their courtyard area to route,
so they shouldn't take more than about 900–1,100 mm². The parts as chosen
need about twice that, so they were split onto two boards.

The symbols are plain generated boxes, not KiCad library symbols. They're
electrically complete, but not pretty. Swapping in library symbols would
break the "generated from code" flow, so keep them unless the project moves
to a hand-drawn schematic.

## vision routing (2026-11-23)

These are the same steps as for fc (see "fc routing"), with `vision` in
place of `fc`. In2.Cu carries the +3V3_ESP pour here.

**Result:** KiCad DRC reports 0 errors, 0 unconnected and 0 schematic-parity
issues. The 24 warnings are all silkscreen. The board has 2062 track
segments and 193 vias, about 1.3 m of track: 441 mm on F.Cu, 544 mm on B.Cu
and 305 mm on In2.Cu. Freerouting got all but 1 of the 141 connections, and
`handroute.py` closed the rest. No copper or via is inside the ESP32-S3
antenna keep-out, on any layer.

**What it took:**

- **`fanout.py` keep-out check:** it used to test only a via's centre
  against the antenna keep-out, which let 11 ground vias overlap the edge
  of it. It now keeps the whole via plus 0.05 mm out. Those 11 vias were
  removed, and the ground pours stay connected without them.
- **J201's +3V3_ESP pin** joins the In2 pour solid, like J200's plane pins
  on fc.
- **Cleanup:** duplicate track segments and one dangling stub were removed.
- **+3V8 widened (2026-11-24):** it was routed at 0.4 mm, partly on In2.Cu
  (0.5 oz) through one via, about 0.5 A at a 20 °C rise against the ESP32-S3's
  WiFi bursts of up to 0.5 A plus whatever J132 / J133 draw. It was ripped up
  and re-routed at 0.8 mm on F.Cu and B.Cu only, with 7 power vias, J201's
  three +3V8 pins tied together on both layers. `handroute.py` re-routed the 7
  signals that had to move (camera I2C, CAM_Y3 / Y4, +2V8_CAM, a +3V3_ESP
  link, STM_BOOT0).
