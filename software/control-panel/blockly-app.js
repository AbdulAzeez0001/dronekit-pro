// DroneKit Blocks: wiring for blockly.html (MIT).
import { DroneLink } from './drone-link.js';
import { FlightProgram } from './program.js';
import { TOOLBOX, STARTER, generate } from './blocks.js';

const Blockly = window.Blockly;
const $ = (id) => document.getElementById(id);

// ---- per-browser settings (shared with the sticks page) ------------------
const store = {
  get(k, d) { try { return localStorage.getItem(k) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* private mode */ } },
};
const theme = store.get('dk.theme', '');
if (theme) document.documentElement.dataset.theme = theme;
const dark = theme === 'dark' || (!theme && matchMedia('(prefers-color-scheme: dark)').matches);

// ---- link ----------------------------------------------------------------
const params = new URLSearchParams(location.search);
const useMock = params.has('mock');
let openSocket;
if (useMock) {
  const { MockDrone } = await import('./mock-drone.js');
  const mock = new MockDrone();
  window.mockDrone = mock;
  openSocket = () => mock.connect();
  $('mockBanner').hidden = false;
  $('sticksLink').href = 'index.html?mock';
}
const link = new DroneLink({ openSocket, maxThrottle: Number(store.get('dk.maxThrottle', 0.7)) });

// ---- messages --------------------------------------------------------------
function say(text, kind = '') {
  const div = document.createElement('div');
  div.textContent = text;
  if (kind) div.className = kind;
  $('out').prepend(div);
  while ($('out').children.length > 100) $('out').lastChild.remove();
}
link.addEventListener('message', (e) => say(e.detail.text, e.detail.kind === 'error' ? 'error' : ''));

// ---- workspace -------------------------------------------------------------
const darkTheme = Blockly.Theme.defineTheme('dk-dark', {
  base: Blockly.Themes.Classic,
  componentStyles: {
    workspaceBackgroundColour: '#0e1116', toolboxBackgroundColour: '#171b22',
    toolboxForegroundColour: '#e8ebf0', flyoutBackgroundColour: '#1d222b',
    flyoutForegroundColour: '#e8ebf0', flyoutOpacity: 1, scrollbarColour: '#5d6673',
    scrollbarOpacity: 0.5, insertionMarkerColour: '#ffffff', insertionMarkerOpacity: 0.3,
    cursorColour: '#d0d0d0',
  },
});
const workspace = Blockly.inject('workspace', {
  toolbox: TOOLBOX,
  theme: dark ? darkTheme : Blockly.Themes.Classic,
  trashcan: true,
  zoom: { controls: true, wheel: true, startScale: 1.0 },
  move: { scrollbars: true, drag: true, wheel: true },
});

// Keep the program in this browser between visits.
const SAVE_KEY = 'dk.blocks';
try {
  const saved = store.get(SAVE_KEY, '');
  Blockly.serialization.workspaces.load(saved ? JSON.parse(saved) : STARTER, workspace);
} catch {
  Blockly.serialization.workspaces.load(STARTER, workspace);
}
const showCode = () => { $('code').textContent = generate(workspace) || '// empty'; };
workspace.addChangeListener((e) => {
  if (e.isUiEvent) return;
  store.set(SAVE_KEY, JSON.stringify(Blockly.serialization.workspaces.save(workspace)));
  showCode();
});
showCode();

// ---- run / stop ------------------------------------------------------------
const program = new FlightProgram(link, { say });

$('runBtn').onclick = async () => {
  if (program.running) return;
  const code = generate(workspace);
  if (!code.trim()) { say('add some blocks first', 'error'); return; }
  say('running');
  render();
  try {
    await program.run(code);
  } catch (e) {
    console.error(e);
  }
  render();
};
const stop = () => { program.stop(); render(); };
$('stopBtn').onclick = stop;
document.addEventListener('keydown', (e) => {
  // Space stops, unless the user is typing in a block field.
  if (e.code === 'Space' && !(e.target instanceof HTMLInputElement) && !e.target.isContentEditable) {
    e.preventDefault();
    stop();
  }
});
// Leaving the page stops the drone.
document.addEventListener('visibilitychange', () => { if (document.hidden) stop(); });
window.addEventListener('pagehide', stop);

// ---- save / open files -----------------------------------------------------
$('codeBtn').onclick = () => {
  $('code').classList.toggle('show');
  $('codeBtn').textContent = $('code').classList.contains('show') ? 'Hide code' : 'Show code';
};
$('saveBtn').onclick = () => {
  const blob = new Blob([JSON.stringify(Blockly.serialization.workspaces.save(workspace), null, 2)],
                        { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'drone-program.json';
  a.click();
  URL.revokeObjectURL(a.href);
};
$('openBtn').onclick = () => $('openFile').click();
$('openFile').onchange = async () => {
  const f = $('openFile').files[0];
  if (!f) return;
  try {
    Blockly.serialization.workspaces.load(JSON.parse(await f.text()), workspace);
    say(`opened ${f.name}`);
  } catch (e) {
    say(`couldn't open ${f.name}: ${e.message}`, 'error');
  }
  $('openFile').value = '';
};

// ---- status ----------------------------------------------------------------
function pill(el, text, cls) { el.textContent = text; el.className = `pill ${cls ?? ''}`; }

function render() {
  const t = link.telemetry;
  const fresh = link.linkFresh;
  if (!link.connected) pill($('pLink'), 'Disconnected', 'bad');
  else if (!fresh) pill($('pLink'), 'No telemetry', 'warn');
  else if (!t.fc_link) pill($('pLink'), 'No flight controller', 'bad');
  else pill($('pLink'), useMock ? 'Pretend drone' : 'Connected', 'ok');
  if (fresh) pill($('pBatt'), `${t.vbat.toFixed(2)} V`, t.vbat < 3.4 ? 'bad' : t.vbat < 3.6 ? 'warn' : 'ok');
  else pill($('pBatt'), '-- V');
  pill($('pArmed'), link.armed ? 'ARMED' : 'Disarmed', link.armed ? 'bad' : '');
  $('runBtn').disabled = program.running || !link.connected;
  $('runBtn').textContent = program.running ? 'Running…' : '▶ Run';
}
link.addEventListener('state', render);
setInterval(render, 250);
link.connect();
render();
