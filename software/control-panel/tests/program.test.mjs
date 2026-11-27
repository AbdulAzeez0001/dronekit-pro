// Tests for the block-program runner against the pretend drone.
// Run from software/control-panel:  node --test tests/
import { test } from 'node:test';
import assert from 'node:assert/strict';

import { DroneLink } from '../drone-link.js';
import { MockDrone } from '../mock-drone.js';
import { FlightProgram } from '../program.js';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function setup() {
  const drone = new MockDrone();
  const link = new DroneLink({ openSocket: () => drone.connect() });
  link.connect();
  await sleep(200);
  const said = [];
  const program = new FlightProgram(link, { say: (t) => said.push(t) });
  return { drone, link, program, said, done: () => { link.close(); drone.stop(); } };
}

test('a whole flight runs and ends disarmed', async () => {
  const { drone, program, said, done } = await setup();
  try {
    await program.run(`
      await drone.arm();
      await drone.takeoff(45, 0.2);
      await drone.move("forward", 20, 0.2);
      await drone.turn("left", 30, 0.2);
      await drone.hover(0.2);
      await drone.land(0.2);
    `);
    await sleep(150);
    assert.equal(drone.fcArmed, false);
    assert.equal(said.filter((s) => s === 'landed').length, 1, 'lands once, not again at the end');
    assert.ok(!said.includes('program finished: landing'));
    assert.ok(said.includes('program finished'));
  } finally { done(); }
});

test('a program that ends while flying lands by itself', async () => {
  const { drone, link, program, said, done } = await setup();
  try {
    await program.run('await drone.arm(); await drone.takeoff(40, 0.1);');
    await sleep(150);
    assert.ok(said.includes('program finished: landing'));
    assert.equal(link.armed, false);
    assert.equal(drone.fcArmed, false);
  } finally { done(); }
});

test('Stop ends the program and kills', async () => {
  const { drone, program, said, done } = await setup();
  try {
    const running = program.run('await drone.arm(); await drone.takeoff(50, 0.1); await drone.hover(30);');
    await sleep(700);
    assert.equal(drone.fcArmed, true);
    program.stop();
    await running;
    await sleep(150);
    assert.equal(drone.fcArmed, false);
    assert.ok(said.some((s) => s.startsWith('stopped')));
  } finally { done(); }
});

test('a kill from elsewhere ends the program', async () => {
  const { drone, link, program, said, done } = await setup();
  try {
    const running = program.run('await drone.arm(); await drone.takeoff(50, 0.1); await drone.hover(30);');
    await sleep(700);
    drone._receive(99, '{"type":"kill"}');     // someone else hits KILL
    await running;
    assert.equal(link.armed, false);
    assert.ok(said.some((s) => s.includes('not armed')));
  } finally { done(); }
});

test('an endless loop can still be stopped', async () => {
  const { program, said, done } = await setup();
  try {
    // What Blockly makes of "repeat while true" with the loop trap.
    const running = program.run('let n = 0; while (true) { await drone.tick(); n++; }');
    await sleep(200);
    program.stop();
    await running;
    assert.ok(said.some((s) => s.startsWith('stopped')));
  } finally { done(); }
});

test('arming refused becomes a readable stop', async () => {
  const { drone, program, said, done } = await setup();
  try {
    drone.armingDisabled = 1 << 2;   // RXLOSS
    await sleep(150);
    await program.run('await drone.arm(); await drone.takeoff(50, 1);');
    assert.ok(said.some((s) => s.includes("won't arm") && s.includes('RXLOSS')));
    assert.equal(drone.fcArmed, false);
  } finally { done(); }
});

test('a bug in the program kills and reports', async () => {
  const { drone, program, said, done } = await setup();
  try {
    await assert.rejects(program.run('await drone.arm(); await drone.takeoff(40, 0.1); undefinedThing();'));
    await sleep(150);
    assert.equal(drone.fcArmed, false);
    assert.ok(said.some((s) => s.startsWith('error')));
  } finally { done(); }
});
