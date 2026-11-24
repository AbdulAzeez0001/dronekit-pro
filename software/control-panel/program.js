// Runs a block program against the drone (MIT).
// The commands match software/dronekit_pcb: arm, takeoff, hover, move,
// turn, land, wait. Every command checks for Stop and for the drone
// disarming, so a program can't keep going after a kill.

export class Stopped extends Error {
  constructor(msg = 'stopped') { super(msg); this.name = 'Stopped'; }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, Number(v) || 0));

export class FlightProgram {
  // link: a DroneLink. say(text): show a line to the user.
  constructor(link, { say = () => {} } = {}) {
    this.link = link;
    this.say = say;
    this.stopped = false;
    this.running = false;
  }

  // Run generated code: the body of an async function taking `drone`.
  async run(code) {
    if (this.running) throw new Error('a program is already running');
    this.stopped = false;
    this.running = true;
    const AsyncFunction = Object.getPrototypeOf(async () => {}).constructor;
    try {
      const body = new AsyncFunction('drone', code);
      await body(this);
      // Finished while still flying: land rather than cut out.
      if (this.link.armed) {
        this.say('program finished: landing');
        await this.land(1.5);
      }
      this.say('program finished');
    } catch (e) {
      if (!this.stopped) this.link.kill();   // stop() has already killed
      if (e instanceof Stopped) this.say(`stopped: ${e.message}`);
      else { this.say(`error: ${e.message}`); throw e; }
    } finally {
      this.running = false;
    }
  }

  stop(reason = 'stop pressed') {
    this.stopped = true;
    this._reason = reason;
    this.link.kill();
  }

  // ---- checks ----------------------------------------------------------------

  _check() {
    if (this.stopped) throw new Stopped(this._reason);
    if (!this.link.connected) throw new Stopped('lost the connection to the drone');
  }

  _checkArmed() {
    this._check();
    if (!this.link.armed) throw new Stopped('the drone is not armed (killed, disarmed or link lost)');
  }

  async _hold(seconds, needArmed = true) {
    const end = Date.now() + clamp(seconds, 0, 600) * 1000;
    for (;;) {
      needArmed ? this._checkArmed() : this._check();
      const left = end - Date.now();
      if (left <= 0) return;
      await sleep(Math.min(50, left));
    }
  }

  // Yields inside loops so a loop with no drone blocks can't freeze the page.
  async tick() {
    this._check();
    await sleep(0);
  }

  // ---- commands (called by generated code) -----------------------------------

  async arm() {
    this._check();
    this.link.setSticks({ roll: 0, pitch: 0, yaw: 0, throttle: 0 });
    this.say('arming');
    try {
      await this.link.arm();
    } catch (e) {
      throw new Stopped(`won't arm: ${e.message}`);
    }
  }

  async takeoff(throttlePercent, seconds) {
    this._checkArmed();
    const target = clamp(throttlePercent, 0, 100) / 100;
    const start = this.link.sticks.throttle;
    const ms = clamp(seconds, 0, 10) * 1000;
    const t0 = Date.now();
    for (;;) {
      this._checkArmed();
      const k = ms === 0 ? 1 : Math.min(1, (Date.now() - t0) / ms);
      this.link.setSticks({ throttle: start + (target - start) * k });
      if (k >= 1) return;
      await sleep(50);
    }
  }

  async hover(seconds) {
    this.link.setSticks({ roll: 0, pitch: 0, yaw: 0 });
    await this._hold(seconds);
  }

  // direction: forward | back | left | right
  async move(direction, powerPercent, seconds) {
    this._checkArmed();
    const p = clamp(powerPercent, 0, 100) / 100;
    const sticks = { forward: { pitch: p }, back: { pitch: -p }, left: { roll: -p }, right: { roll: p } }[direction];
    if (!sticks) throw new Error(`unknown direction ${direction}`);
    this.link.setSticks({ roll: 0, pitch: 0, yaw: 0, ...sticks });
    try {
      await this._hold(seconds);
    } finally {
      this.link.setSticks({ roll: 0, pitch: 0, yaw: 0 });
    }
  }

  // direction: left | right
  async turn(direction, powerPercent, seconds) {
    this._checkArmed();
    const p = clamp(powerPercent, 0, 100) / 100;
    this.link.setSticks({ roll: 0, pitch: 0, yaw: direction === 'left' ? -p : p });
    try {
      await this._hold(seconds);
    } finally {
      this.link.setSticks({ yaw: 0 });
    }
  }

  async land(seconds) {
    this._check();
    if (this.link.armed) {
      const start = this.link.sticks.throttle;
      const ms = clamp(seconds, 0, 10) * 1000;
      const t0 = Date.now();
      this.link.setSticks({ roll: 0, pitch: 0, yaw: 0 });
      for (;;) {
        this._check();
        if (!this.link.armed) break;
        const k = ms === 0 ? 1 : Math.min(1, (Date.now() - t0) / ms);
        this.link.setSticks({ throttle: start * (1 - k) });
        if (k >= 1) break;
        await sleep(50);
      }
    }
    this.link.disarm();
    // Wait for the drone to report it (telemetry is 10 Hz), so a check
    // straight after doesn't still see "armed".
    const t0 = Date.now();
    while (this.link.armed && Date.now() - t0 < 1000) await sleep(20);
    this.say('landed');
  }

  // Wait without touching the sticks. Works disarmed too.
  async wait(seconds) {
    await this._hold(seconds, false);
  }

  battery() {
    return this.link.telemetry?.vbat ?? 0;
  }

  print(text) {
    this.say(String(text));
  }
}
