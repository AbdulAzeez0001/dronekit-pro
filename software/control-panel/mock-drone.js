// A pretend drone for trying the panel with no hardware (MIT).
// Follows the firmware's rules (firmware/esp32/src/main.cpp,
// flight_link.cpp), like software/dronekit_pcb/src/dronekit_pcb/sim.py:
// one pilot, 0.5 s control timeout, arm only at low throttle, kill from
// anyone, telemetry at 10 Hz. Betaflight is reduced to "arms when asked,
// unless an arming-disable flag is set".
//
// Open the panel with ?mock to use it.

const CONTROL_TIMEOUT_MS = 500;
const ARM_MAX_THROTTLE = 0.05;

export class MockDrone {
  constructor({ vbat = 4.1 } = {}) {
    this.clients = new Map();
    this.nextId = 1;
    this.pilot = 0;
    this.lastControl = 0;
    this.sticks = { roll: 0, pitch: 0, yaw: 0, throttle: 0 };
    this.armedCmd = false;
    this.fcArmed = false;
    this.fcLink = true;
    this.armingDisabled = 0;
    this.vbat = vbat;
    this.heading = 0;
    this.roll = 0;
    this.pitch = 0;
    this._last = Date.now();
    this._lastTlm = 0;
    this._timer = setInterval(() => this._tick(), 10);
  }

  stop() {
    clearInterval(this._timer);
    for (const s of [...this.clients.values()]) s.close();
  }

  // A WebSocket-like object connected to this drone.
  connect() {
    const id = this.nextId++;
    const drone = this;
    const sock = {
      readyState: 0,
      onopen: null, onmessage: null, onclose: null,
      send(text) {
        if (sock.readyState !== 1) throw new Error('closed');
        drone._receive(id, text);
      },
      close() {
        if (sock.readyState === 3) return;
        sock.readyState = 3;
        drone._disconnect(id);
        setTimeout(() => sock.onclose?.({}), 0);
      },
      _deliver(obj) {
        if (sock.readyState === 1) setTimeout(() => sock.onmessage?.({ data: JSON.stringify(obj) }), 0);
      },
    };
    this.clients.set(id, sock);
    setTimeout(() => {
      sock.readyState = 1;
      sock.onopen?.({});
      sock._deliver({ type: 'hello', api: 1, fw: 'mock', mode: 'code', client_id: id });
    }, 0);
    return sock;
  }

  _say(id, type, msg) {
    const targets = id ? [this.clients.get(id)] : [...this.clients.values()];
    for (const s of targets) s?._deliver({ type, msg });
  }

  _dropPilot(why) {
    this.sticks = { roll: 0, pitch: 0, yaw: 0, throttle: 0 };
    this.armedCmd = false;
    this.pilot = 0;
    this._say(0, 'event', why);
  }

  _receive(id, text) {
    let m;
    try { m = JSON.parse(text); } catch { return this._say(id, 'error', 'bad JSON'); }
    const c = (v, lo, hi) => Math.max(lo, Math.min(hi, Number(v) || 0));
    switch (m.type) {
      case 'control':
        if (this.pilot && this.pilot !== id) return this._say(id, 'error', 'another client is the pilot');
        this.pilot = id;
        this.lastControl = Date.now();
        this.sticks = {
          roll: c(m.roll, -1, 1), pitch: c(m.pitch, -1, 1),
          yaw: c(m.yaw, -1, 1), throttle: c(m.throttle, 0, 1),
        };
        break;
      case 'arm':
        if (this.pilot !== id) return this._say(id, 'error', 'only the pilot can arm; send control first');
        if (this.sticks.throttle > ARM_MAX_THROTTLE) return this._say(id, 'error', 'throttle must be at the bottom to arm');
        if (!this.fcLink) return this._say(id, 'error', 'no link to the flight controller');
        this.armedCmd = true;
        break;
      case 'disarm':
        this.armedCmd = false;
        this._say(0, 'event', 'disarmed');
        break;
      case 'kill':
        this._dropPilot('kill: disarmed, pilot dropped');
        break;
      default:
        this._say(id, 'error', 'unknown type');
    }
  }

  _disconnect(id) {
    this.clients.delete(id);
    if (id === this.pilot) this._dropPilot('pilot disconnected: disarmed');
  }

  _tick() {
    const now = Date.now();
    const dt = (now - this._last) / 1000;
    this._last = now;
    if (this.pilot && now - this.lastControl > CONTROL_TIMEOUT_MS) {
      this._dropPilot('pilot went quiet: disarmed');
    }
    if (this.armedCmd && !this.fcArmed && this.armingDisabled === 0) this.fcArmed = true;
    if (!this.armedCmd) this.fcArmed = false;

    // Toy attitude: the angle follows the stick, a bit sluggishly.
    const k = Math.min(1, dt * 8);
    const on = this.fcArmed ? 1 : 0;
    this.roll += (this.sticks.roll * 35 * on - this.roll) * k;
    this.pitch += (this.sticks.pitch * 35 * on - this.pitch) * k;
    this.heading = (this.heading + this.sticks.yaw * 180 * dt * on + 360) % 360;
    this.vbat = Math.max(3.3, this.vbat - this.sticks.throttle * on * 0.002 * dt);

    if (now - this._lastTlm >= 100) {
      this._lastTlm = now;
      const t = {
        type: 'telemetry', pilot_id: this.pilot, armed_cmd: this.armedCmd, armed: this.fcArmed,
        arming_disabled: this.armingDisabled, fc_link: this.fcLink,
        vbat: Math.round(this.vbat * 100) / 100,
        roll: Math.round(this.roll * 10) / 10, pitch: Math.round(this.pitch * 10) / 10,
        heading: Math.round(this.heading),
      };
      for (const s of this.clients.values()) s._deliver(t);
    }
  }
}
