# Board — every block merged into one KiCad schematic

`build_board.py` merges all ten circuit-as-code blocks into one board:

| File | What it is |
|---|---|
| `board.kicad_pro` | KiCad project: open this in KiCad 8 |
| `board.kicad_sch` | one-sheet schematic, 155 parts |
| `board.net` | the same circuit as a KiCad netlist (116 nets) |

**These three files are generated, so don't hand-edit them.** Change the
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
>>> wrote board.net, board.kicad_sch, board.kicad_pro
>>> schematic connectivity re-read from file: matches the netlist
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

## Using it in KiCad 8

1. Open `board.kicad_pro`, then the schematic.
2. **Run ERC.** It hasn't been run inside KiCad yet: KiCad wasn't available
   when this was generated.
3. **Tools > Update PCB from Schematic** pulls the footprints into
   `board.kicad_pcb`. Most footprints are KiCad stock. These need adding or
   checking first:
   - `TI:RNM0015A` (TPS63070) and `TI:RSE0010A` (TS3USB221A USB switch):
     import TI's footprints.
   - `Package_LGA:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y` (ICM-42688-P):
     check it against the datasheet land pattern.
   - The solder-pad parts (battery, motors, receiver, buzzer, SWD, ESP UART0) use pin
     headers as placeholder footprints. Replace them with pad footprints.

The symbols are plain generated boxes, not KiCad library symbols. They're
electrically complete, but not pretty. Swapping in library symbols would
break the "generated from code" flow, so keep them unless the project moves
to a hand-drawn schematic.
