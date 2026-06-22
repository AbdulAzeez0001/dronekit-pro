# Software (MIT)

## dronekit_pcb/
The pip package. `Drone('192.168.4.1')`, arm/takeoff/move/land over the
WebSocket API. Build and unit-test against a simulated drone object first;
swap in the real socket later.

## control-panel/
The browser UI served at 192.168.4.1, plus the Blockly page. Pure HTML/JS,
fully testable in a browser against a mock backend. No hardware needed.
