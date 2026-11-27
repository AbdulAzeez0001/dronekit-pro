// DroneKit Pro control panel (MIT). Mode 2 sticks:
// left = throttle (stays put) + yaw (springs back), right = roll + pitch.
import { DroneLink, armingDisableNames } from './drone-link.js';
import { Stick } from './stick.js';

const $ = (id) => document.getElementById(id);

// ---- settings (per device, in this browser only) -------------------------
const store = {
  get(k, d) { try { return localStorage.getItem(k) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* private mode */ } },
};
const applyTheme = (t) => {
  if (t) document.documentElement.dataset.theme = t;
  else delete document.documentElement.dataset.theme;
};
applyTheme(store.get('dk.theme', ''));

// ---- link: the real drone, or the pretend one with ?mock -----------------
const useMock = new URLSearchParams(location.search).has('mock');
let openSocket;
if (useMock) {
  const { MockDrone } = await import('./mock-drone.js');
  const mock = new MockDrone();
  window.mockDrone = mock;          // for poking at it from the console
  openSocket = () => mock.connect();
  $('mockBanner').hidden = false;
  $('blocksLink').href = 'blockly.html?mock';
}
const link = new DroneLink({ openSocket, maxThrottle: Number(store.get('dk.maxThrottle', 0.7)) });

// ---- sticks --------------------------------------------------------------
const left = new Stick($('leftStick'), {
  springX: true, springY: false, y: -1,
  onChange: (x, y) => { link.setSticks({ yaw: x, throttle: (y + 1) / 2 }); render(); },
});
const right = new Stick($('rightStick'), {
  onChange: (x, y) => { link.setSticks({ roll: x, pitch: y }); render(); },
});
const throttleDown = () => left.set(0, -1);

// ---- buttons ---------------------------------------------------------------
let armError = '';
$('armBtn').onclick = async () => {
  armError = '';
  try {
    await link.arm();
  } catch (e) {
    armError = e.message;
  }
  render();
};
$('disarmBtn').onclick = () => { throttleDown(); link.disarm(); };
const kill = () => { throttleDown(); right.set(0, 0); link.kill(); render(); };
$('killBtn').onclick = kill;
document.addEventListener('keydown', (e) => {
  if (e.code === 'Space') { e.preventDefault(); kill(); }
});
// Leaving the page (another app, screen off) stops the drone.
document.addEventListener('visibilitychange', () => { if (document.hidden) kill(); });
window.addEventListener('pagehide', kill);

$('settingsBtn').onclick = () => {
  $('maxThr').value = link.maxThrottle;
  $('maxThrVal').textContent = `${Math.round(link.maxThrottle * 100)}%`;
  $('theme').value = store.get('dk.theme', '');
  $('settings').showModal();
};
$('maxThr').oninput = () => {
  link.maxThrottle = Number($('maxThr').value);
  $('maxThrVal').textContent = `${Math.round(link.maxThrottle * 100)}%`;
  store.set('dk.maxThrottle', link.maxThrottle);
  link.setSticks({});
};
$('theme').onchange = () => { store.set('dk.theme', $('theme').value); applyTheme($('theme').value); };

// ---- log -------------------------------------------------------------------
link.addEventListener('message', (e) => {
  const div = document.createElement('div');
  div.textContent = e.detail.text;
  if (e.detail.kind === 'error') div.className = 'error';
  $('log').prepend(div);
  while ($('log').children.length > 20) $('log').lastChild.remove();
});

// ---- drawing ---------------------------------------------------------------
function pill(el, text, cls) {
  el.textContent = text;
  el.className = `pill ${cls ?? ''}`;
}

function render() {
  const t = link.telemetry;
  const fresh = link.linkFresh;

  if (!link.connected) pill($('pLink'), 'Disconnected', 'bad');
  else if (!fresh) pill($('pLink'), 'No telemetry', 'warn');
  else if (!t.fc_link) pill($('pLink'), 'No flight controller', 'bad');
  else pill($('pLink'), useMock ? 'Pretend drone' : 'Connected', 'ok');

  if (fresh) {
    const v = t.vbat;
    pill($('pBatt'), `${v.toFixed(2)} V`, v < 3.4 ? 'bad' : v < 3.6 ? 'warn' : 'ok');
  } else {
    pill($('pBatt'), '-- V');
  }
  pill($('pArmed'), link.armed ? 'ARMED' : 'Disarmed', link.armed ? 'bad' : '');
  pill($('pPilot'), link.isPilot ? 'In control' : 'Watching', link.isPilot ? 'ok' : '');

  const roll = fresh ? t.roll : 0, pitch = fresh ? t.pitch : 0, head = fresh ? t.heading : 0;
  $('horizon').setAttribute('transform', `rotate(${-roll}) translate(0 ${pitch * 2})`);
  $('rRoll').textContent = `${Math.round(roll)}°`;
  $('rPitch').textContent = `${Math.round(pitch)}°`;
  $('rHead').textContent = `${Math.round(head)}°`;

  const s = link.sticks;
  $('leftLabel').textContent = `Throttle ${Math.round(s.throttle * 100)}% · Yaw ${s.yaw.toFixed(2)}`;
  $('rightLabel').textContent = `Roll ${s.roll.toFixed(2)} · Pitch ${s.pitch.toFixed(2)}`;

  // Why can't I arm?
  let why = '';
  if (!link.connected) why = 'Not connected. Join the drone\'s Wi-Fi (DroneKit-XXXX).';
  else if (fresh && !t.fc_link) why = 'The ESP32 can\'t hear the flight controller.';
  else if (!link.armed && s.throttle > 0.05) why = 'Throttle to the bottom to arm.';
  else if (!link.armed && armError) why = armError;
  $('why').textContent = why;
  const blocked = fresh && !link.armed ? armingDisableNames(t.arming_disabled) : [];
  $('chips').replaceChildren(...blocked.map((n) => {
    const c = document.createElement('span');
    c.className = 'chip';
    c.textContent = n;
    return c;
  }));

  $('armBtn').disabled = !link.connected || link.armed || s.throttle > 0.05 || (fresh && !t.fc_link);
  $('disarmBtn').disabled = !link.armed;
}

link.addEventListener('state', render);
setInterval(render, 250);   // also catches telemetry going stale
link.connect();
render();
