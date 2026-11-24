# Software (MIT)

## dronekit_pcb/
The pip package. `Drone('192.168.4.1')`, arm/takeoff/move/land over the
WebSocket API v1, plus a simulated drone (`dronekit_pcb.sim`) that follows
the firmware's rules. See `dronekit_pcb/README.md`.

## control-panel/
The browser UI served at 192.168.4.1: touch sticks, attitude, arm/kill.
Pure HTML/JS, testable against a pretend drone (`?mock`). See
`control-panel/README.md`. The Blockly page is still to do.
