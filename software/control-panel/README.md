# DroneKit Pro control panel (MIT)

The browser pages for **Code mode**, served by the drone at
`http://192.168.4.1/`: **Sticks** (`index.html`) to fly by hand, and
**Blocks** (`blockly.html`) to program it by dragging blocks. Plain HTML, CSS and JavaScript modules, with no
build step and nothing loaded from the internet (the drone's Wi-Fi has
none).

- **Two touch sticks (Mode 2):**
  - left: throttle (stays where you leave it) and yaw (springs back);
  - right: roll and pitch (both spring back).
- **Attitude indicator** with roll, pitch and heading.
- **Arm, Disarm, KILL.** KILL is always on screen; the space bar also kills.
- **Status:** link, battery (amber below 3.6 V, red below 3.4 V), armed,
  and whether this device is in control.
- **Why it won't arm,** including Betaflight's blocking checks by name.
- **Settings:** max throttle and theme, kept in this browser only.

## Blocks (`blockly.html`)

Drag blocks, press **Run**. Drone blocks:

| Block | What it does |
|---|---|
| arm the motors | Arm, throttle at zero |
| take off to N % throttle over N s | Ramp the throttle up (no height hold) |
| hover for N s | Keep the throttle, level |
| move forward/back/left/right at N % for N s | Lean, then level again |
| turn left/right at N % for N s | Spin on the spot |
| land over N s | Ramp the throttle down, then disarm |
| wait N s, battery volts, say … | Timing, the battery, messages |

Loops, logic, maths, text and variables are Blockly's own blocks.

- **STOP** (or the space bar) ends the program and kills the drone.
- Every loop pass checks STOP, so even "repeat forever" can be stopped.
- A program that ends while still flying lands by itself.
- A kill from another device, a lost link, or a refused arm ends the
  program with the reason in Messages.
- **Show code** shows the JavaScript the blocks make.
- The program is kept in this browser; **Save** and **Open** move it as a
  `.json` file.

It works on a phone but is easier on a tablet or laptop.

## Safety

The same rules as `software/dronekit_pcb`:

- The page only takes control when you press **Arm**. Until then it
  watches, and another device can fly.
- A failed arm lets go of control again.
- Arming needs the throttle stick at the bottom.
- **Leaving the page stops the drone:** another app, the screen turning
  off, closing the tab. If the page freezes, the firmware disarms within
  0.5 s anyway.
- Any device can KILL.

## Try it with no drone

```
cd software/control-panel
python -m http.server 8765
```

Open `http://localhost:8765/?mock` (sticks) or
`http://localhost:8765/blockly.html?mock` (blocks). An amber banner shows it's a pretend
drone (`mock-drone.js`), which follows the firmware's rules. From the
browser console, `mockDrone.armingDisabled = 1 << 7` makes it refuse to
arm with THROTTLE.

## Tests

```
cd software/control-panel
node --test tests/
```

17 tests against the pretend drone:
- 10 for the link logic (`drone-link.js`): arming, max throttle,
  Betaflight blocks, two devices, kill, closing and freezing the page;
- 7 for the block-program runner (`program.js`): a full flight, landing
  at the end, STOP, a kill from elsewhere, an endless loop, a refused arm,
  and a bug in the program.

## Put it on the drone

From `firmware/esp32`: `pio run -t uploadfs`. That copies this folder into
the ESP32's flash; see `firmware/esp32/README.md`. The folder is about
1.1 MB, almost all of it Blockly, against a flash file area of about
1.4 MB, so keep big additions out of it.

## Files

| File | What |
|---|---|
| `index.html`, `style.css` | The page (light and dark) |
| `app.js` | Wiring: sticks, buttons, display |
| `drone-link.js` | WebSocket API v1 client |
| `stick.js` | Touch / mouse stick |
| `mock-drone.js` | Pretend drone for `?mock` and the tests |
| `blockly.html`, `blockly-app.js` | The Blocks page |
| `blocks.js` | Drone blocks and the code they make |
| `program.js` | Runs a block program: STOP, kill and loop checks |
| `vendor/blockly/` | Blockly 11.2.1 (Apache-2.0), stored here for offline use |
| `tests/` | Node tests |
