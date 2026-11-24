# Software (MIT)

## dronekit_pcb/
The pip package. `Drone('192.168.4.1')`, arm/takeoff/move/land over the
WebSocket API v1, plus a simulated drone (`dronekit_pcb.sim`) that follows
the firmware's rules. See `dronekit_pcb/README.md`.

## control-panel/
The browser UI served at 192.168.4.1, plus the Blockly page. Pure HTML/JS,
fully testable in a browser against a mock backend. No hardware needed.
