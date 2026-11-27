// DroneKit Pro control panel: the WebSocket API v1 client (MIT).
// Same rules as software/dronekit_pcb: only claim the pilot role when the
// user wants to fly (Arm), send sticks at 20 Hz while flying, stop on Kill.
// See firmware/esp32/src/api.h for the messages.

export const API_VERSION = 1;
const CONTROL_PERIOD_MS = 50;
const TELEMETRY_TIMEOUT_MS = 1000;

// Betaflight 4.4 / 4.5 arming-disable flags, bit by bit.
export const ARMING_DISABLE_FLAGS = [
  'NO_GYRO', 'FAILSAFE', 'RXLOSS', 'BADRX', 'BOXFAILSAFE', 'RUNAWAY_TAKEOFF',
  'CRASH_DETECTED', 'THROTTLE', 'ANGLE', 'BOOT_GRACE_TIME', 'NOPREARM', 'LOAD',
  'CALIBRATING', 'CLI', 'CMS_MENU', 'BST', 'MSP', 'PARALYZE', 'GPS',
  'RESC', 'RPMFILTER', 'REBOOT_REQUIRED', 'DSHOT_BITBANG', 'ACC_CALIBRATION',
  'MOTOR_PROTOCOL', 'ARMSWITCH',
];

export function armingDisableNames(flags) {
  const names = [];
  for (let bit = 0; bit < 32; bit++) {
    if ((flags >>> bit) & 1) names.push(ARMING_DISABLE_FLAGS[bit] ?? `BIT${bit}`);
  }
  return names;
}

const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, Number(v) || 0));

// Events: 'state' (connection/pilot/telemetry changed), 'message'
// ({detail: {kind: 'error'|'event'|'info', text}}).
export class DroneLink extends EventTarget {
  // openSocket(): returns a WebSocket-like object (send, close, onopen,
  // onmessage, onclose). Defaults to ws://<host>/ws.
  constructor({ openSocket, maxThrottle = 0.7, now = () => Date.now() } = {}) {
    super();
    this.openSocket = openSocket ?? (() => new WebSocket(`ws://${location.host}/ws`));
    this.maxThrottle = clamp(maxThrottle, 0, 1);
    this.now = now;
    this.socket = null;
    this.connected = false;
    this.clientId = null;
    this.telemetry = null;      // latest telemetry message, plus .time
    this.flying = false;        // we send sticks and so claim the pilot role
    this.sticks = { roll: 0, pitch: 0, yaw: 0, throttle: 0 };
    this._timer = null;
    this._closedByUs = false;
  }

  // ---- connection ----------------------------------------------------------

  connect() {
    this._closedByUs = false;
    const ws = this.openSocket();
    this.socket = ws;
    ws.onopen = () => { this.connected = true; this._changed(); };
    ws.onmessage = (e) => this._onMessage(e.data);
    ws.onclose = () => {
      if (this.socket !== ws) return;
      this.connected = false;
      this.clientId = null;
      this.telemetry = null;
      this._stopFlying();
      this._changed();
      this._say('event', 'connection lost');
      if (!this._closedByUs) setTimeout(() => this.connect(), 1000);
    };
  }

  close() {
    this._closedByUs = true;
    this.kill();
    this.socket?.close();
  }

  get linkFresh() {
    return !!this.telemetry && this.now() - this.telemetry.time < TELEMETRY_TIMEOUT_MS;
  }

  get isPilot() {
    return !!this.telemetry && this.clientId != null && this.telemetry.pilot_id === this.clientId;
  }

  get armed() { return !!this.telemetry?.armed; }

  // ---- sticks --------------------------------------------------------------

  setSticks({ roll = this.sticks.roll, pitch = this.sticks.pitch, yaw = this.sticks.yaw,
              throttle = this.sticks.throttle } = {}) {
    this.sticks = {
      roll: clamp(roll, -1, 1),
      pitch: clamp(pitch, -1, 1),
      yaw: clamp(yaw, -1, 1),
      throttle: clamp(throttle, 0, this.maxThrottle),
    };
  }

  // ---- commands ------------------------------------------------------------

  // Take the pilot role and arm. Resolves when Betaflight reports armed;
  // rejects with a readable reason.
  async arm({ timeoutMs = 3000 } = {}) {
    if (!this.connected) throw new Error('not connected to the drone');
    if (this.sticks.throttle > 0.05) throw new Error('put the throttle at the bottom first');
    this._startFlying();
    if (!(await this._waitFor(() => this.isPilot, 1000))) {
      this._stopFlying();
      throw new Error('another device is flying this drone');
    }
    const errorsBefore = this._errors;
    this._send({ type: 'arm' });
    const ok = await this._waitFor(() => this.armed || this._errors !== errorsBefore, timeoutMs);
    if (this.armed) return;
    // Didn't arm: let go of the pilot role so another device can fly.
    this._stopFlying();
    this._changed();
    if (this._errors !== errorsBefore) throw new Error(this._lastError);
    const blocked = armingDisableNames(this.telemetry?.arming_disabled ?? 0);
    throw new Error(blocked.length ? `Betaflight won't arm: ${blocked.join(', ')}`
                                   : ok ? 'arm refused' : "Betaflight didn't arm in time");
  }

  disarm() {
    this.setSticks({ throttle: 0 });
    this._send({ type: 'disarm' });
  }

  // Stop now and give up the pilot role. Works from any device.
  kill() {
    this.setSticks({ roll: 0, pitch: 0, yaw: 0, throttle: 0 });
    this._stopFlying();
    this._send({ type: 'kill' });
  }

  // ---- internals -----------------------------------------------------------

  _errors = 0;
  _lastError = '';

  _send(msg) {
    if (this.socket && this.connected) {
      try { this.socket.send(JSON.stringify(msg)); } catch { /* onclose follows */ }
    }
  }

  _startFlying() {
    if (this._timer) return;
    this.flying = true;
    const tick = () => this._send({ type: 'control', ...this.sticks });
    tick();
    this._timer = setInterval(tick, CONTROL_PERIOD_MS);
    this._changed();
  }

  _stopFlying() {
    if (this._timer) clearInterval(this._timer);
    this._timer = null;
    this.flying = false;
  }

  _onMessage(text) {
    let m;
    try { m = JSON.parse(text); } catch { return; }
    switch (m.type) {
      case 'hello':
        if (m.api !== API_VERSION) {
          this._say('error', `the drone speaks API ${m.api}; this page speaks ${API_VERSION}`);
        }
        this.clientId = m.client_id;
        this._changed();
        break;
      case 'telemetry':
        this.telemetry = { ...m, time: this.now() };
        this._changed();
        break;
      case 'error':
        this._errors++;
        this._lastError = String(m.msg ?? '');
        this._say('error', this._lastError);
        break;
      case 'event':
        this._say('event', String(m.msg ?? ''));
        break;
    }
  }

  _say(kind, text) {
    this.dispatchEvent(new CustomEvent('message', { detail: { kind, text } }));
  }

  _changed() {
    this.dispatchEvent(new Event('state'));
  }

  _waitFor(cond, timeoutMs) {
    return new Promise((resolve) => {
      const end = this.now() + timeoutMs;
      const check = () => {
        if (cond()) return resolve(true);
        if (this.now() >= end) return resolve(false);
        setTimeout(check, 10);
      };
      check();
    });
  }
}
