# DroneKit Pro control panel (MIT)

The browser page for flying in **Code mode**, served by the drone at
`http://192.168.4.1/`. Plain HTML, CSS and JavaScript modules, with no
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

Open `http://localhost:8765/?mock`. An amber banner shows it's a pretend
drone (`mock-drone.js`), which follows the firmware's rules. From the
browser console, `mockDrone.armingDisabled = 1 << 7` makes it refuse to
arm with THROTTLE.

## Tests

```
cd software/control-panel
node --test tests/
```

10 tests of the link logic (`drone-link.js`) against the pretend drone:
arming, max throttle, Betaflight blocks, two devices, kill, closing and
freezing the page.

## Put it on the drone

From `firmware/esp32`: `pio run -t uploadfs`. That copies this folder into
the ESP32's flash; see `firmware/esp32/README.md`.

## Files

| File | What |
|---|---|
| `index.html`, `style.css` | The page (light and dark) |
| `app.js` | Wiring: sticks, buttons, display |
| `drone-link.js` | WebSocket API v1 client |
| `stick.js` | Touch / mouse stick |
| `mock-drone.js` | Pretend drone for `?mock` and the tests |
| `tests/link.test.mjs` | Node tests |

Not here yet: the Blockly page. It needs the Blockly library stored on the
drone, since there's no internet on its Wi-Fi.
