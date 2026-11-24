// Tests for the panel's link logic against the pretend drone.
// Run from software/control-panel:  node --test tests/
import { test } from 'node:test';
import assert from 'node:assert/strict';

import { DroneLink, armingDisableNames } from '../drone-link.js';
import { MockDrone } from '../mock-drone.js';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function setup(opts = {}) {
  const drone = new MockDrone();
  const link = new DroneLink({ openSocket: () => drone.connect(), ...opts });
  link.connect();
  await sleep(200);
  return { drone, link, done: () => { link.close(); drone.stop(); } };
}

test('connects and receives telemetry', async () => {
  const { link, done } = await setup();
  try {
    assert.ok(link.connected);
    assert.ok(link.clientId > 0);
    assert.ok(link.linkFresh);
    assert.equal(link.isPilot, false, 'watching until Arm');
  } finally { done(); }
});

test('arm takes the pilot role and arms', async () => {
  const { drone, link, done } = await setup();
  try {
    await link.arm();
    assert.ok(link.armed);
    assert.ok(link.isPilot);
    link.setSticks({ throttle: 0.4, pitch: 0.5 });
    await sleep(120);
    assert.equal(drone.sticks.throttle, 0.4);
    assert.equal(drone.sticks.pitch, 0.5);
  } finally { done(); }
});

test('arm refuses with the throttle up', async () => {
  const { link, done } = await setup();
  try {
    link.setSticks({ throttle: 0.3 });
    await assert.rejects(link.arm(), /throttle/);
    assert.equal(link.flying, false);
  } finally { done(); }
});

test('max throttle caps what is sent', async () => {
  const { drone, link, done } = await setup({ maxThrottle: 0.3 });
  try {
    await link.arm();
    link.setSticks({ throttle: 1 });
    await sleep(120);
    assert.equal(drone.sticks.throttle, 0.3);
  } finally { done(); }
});

test('Betaflight blocks are named', async () => {
  const { drone, link, done } = await setup();
  try {
    drone.armingDisabled = (1 << 7) | (1 << 25);
    await sleep(150);
    await assert.rejects(link.arm({ timeoutMs: 400 }), /THROTTLE, ARMSWITCH/);
    assert.equal(link.flying, false, 'a failed arm lets go of the pilot role');
  } finally { done(); }
});

test('a watcher cannot arm while someone flies, but can kill', async () => {
  const drone = new MockDrone();
  const a = new DroneLink({ openSocket: () => drone.connect() });
  const b = new DroneLink({ openSocket: () => drone.connect() });
  a.connect(); b.connect();
  await sleep(200);
  try {
    await a.arm();
    await assert.rejects(b.arm(), /another device/);
    b.kill();
    await sleep(150);
    assert.equal(drone.fcArmed, false);
    assert.equal(a.armed, false);
  } finally { a.close(); b.close(); drone.stop(); }
});

test('kill stops sending, so the pilot role is released', async () => {
  const { drone, link, done } = await setup();
  try {
    await link.arm();
    link.kill();
    await sleep(150);
    assert.equal(link.flying, false);
    assert.equal(drone.pilot, 0);
    assert.equal(drone.fcArmed, false);
  } finally { done(); }
});

test('closing the page disarms', async () => {
  const { drone, link, done } = await setup();
  try {
    await link.arm();
    link.close();
    await sleep(100);
    assert.equal(drone.fcArmed, false);
  } finally { done(); }
});

test('a frozen page disarms within 0.5 s (firmware timeout)', async () => {
  const { drone, link, done } = await setup();
  try {
    await link.arm();
    link._stopFlying();          // the page stops sending, as if frozen
    await sleep(650);
    assert.equal(drone.fcArmed, false);
  } finally { done(); }
});

test('flag names', () => {
  assert.deepEqual(armingDisableNames(0), []);
  assert.deepEqual(armingDisableNames(1 << 2), ['RXLOSS']);
  assert.deepEqual(armingDisableNames(2 ** 31), ['BIT31']);
});
