// Drone blocks for Blockly, and the code they generate (MIT).
// Each block becomes `await drone.<command>(...)` on a FlightProgram
// (program.js). Uses the global Blockly and javascript loaded by
// blockly.html from vendor/blockly/.

const Blockly = window.Blockly;
const { javascriptGenerator: js, Order } = window.javascript;

export const DRONE_COLOUR = 210;

Blockly.common.defineBlocksWithJsonArray([
  {
    type: 'dk_arm',
    message0: 'arm the motors',
    previousStatement: null, nextStatement: null, colour: 0,
    tooltip: 'Start the motors spinning slowly. The throttle must be at zero.',
  },
  {
    type: 'dk_takeoff',
    message0: 'take off to %1 %% throttle over %2 s',
    args0: [
      { type: 'field_number', name: 'THROTTLE', value: 45, min: 0, max: 100, precision: 1 },
      { type: 'field_number', name: 'SECONDS', value: 1, min: 0, max: 10 },
    ],
    previousStatement: null, nextStatement: null, colour: DRONE_COLOUR,
    tooltip: 'Raise the throttle gradually. There is no height hold: find the hover throttle with short hops.',
  },
  {
    type: 'dk_hover',
    message0: 'hover for %1 s',
    args0: [{ type: 'input_value', name: 'SECONDS', check: 'Number' }],
    inputsInline: true,
    previousStatement: null, nextStatement: null, colour: DRONE_COLOUR,
    tooltip: 'Keep the throttle, sticks centred.',
  },
  {
    type: 'dk_move',
    message0: 'move %1 at %2 %% for %3 s',
    args0: [
      { type: 'field_dropdown', name: 'DIR', options: [['forward', 'forward'], ['back', 'back'], ['left', 'left'], ['right', 'right']] },
      { type: 'field_number', name: 'POWER', value: 20, min: 0, max: 100, precision: 1 },
      { type: 'input_value', name: 'SECONDS', check: 'Number' },
    ],
    inputsInline: true,
    previousStatement: null, nextStatement: null, colour: DRONE_COLOUR,
    tooltip: 'Lean the drone, then level it again.',
  },
  {
    type: 'dk_turn',
    message0: 'turn %1 at %2 %% for %3 s',
    args0: [
      { type: 'field_dropdown', name: 'DIR', options: [['left', 'left'], ['right', 'right']] },
      { type: 'field_number', name: 'POWER', value: 30, min: 0, max: 100, precision: 1 },
      { type: 'input_value', name: 'SECONDS', check: 'Number' },
    ],
    inputsInline: true,
    previousStatement: null, nextStatement: null, colour: DRONE_COLOUR,
    tooltip: 'Spin on the spot.',
  },
  {
    type: 'dk_land',
    message0: 'land over %1 s',
    args0: [{ type: 'field_number', name: 'SECONDS', value: 2, min: 0, max: 10 }],
    previousStatement: null, nextStatement: null, colour: 0,
    tooltip: 'Lower the throttle gradually, then stop the motors.',
  },
  {
    type: 'dk_wait',
    message0: 'wait %1 s',
    args0: [{ type: 'input_value', name: 'SECONDS', check: 'Number' }],
    inputsInline: true,
    previousStatement: null, nextStatement: null, colour: 120,
    tooltip: 'Wait without changing anything.',
  },
  {
    type: 'dk_battery',
    message0: 'battery volts',
    output: 'Number', colour: 120,
    tooltip: 'The battery voltage. A 1S battery is full at 4.2 V and should land by 3.5 V.',
  },
  {
    type: 'dk_say',
    message0: 'say %1',
    args0: [{ type: 'input_value', name: 'TEXT' }],
    previousStatement: null, nextStatement: null, colour: 160,
    tooltip: 'Show a message under the program.',
  },
]);

const seconds = (block, name, fallback = '1') =>
  js.valueToCode(block, name, Order.NONE) || fallback;

js.forBlock.dk_arm = () => 'await drone.arm();\n';
js.forBlock.dk_takeoff = (b) =>
  `await drone.takeoff(${Number(b.getFieldValue('THROTTLE'))}, ${Number(b.getFieldValue('SECONDS'))});\n`;
js.forBlock.dk_hover = (b) => `await drone.hover(${seconds(b, 'SECONDS')});\n`;
js.forBlock.dk_move = (b) =>
  `await drone.move(${JSON.stringify(b.getFieldValue('DIR'))}, ${Number(b.getFieldValue('POWER'))}, ${seconds(b, 'SECONDS')});\n`;
js.forBlock.dk_turn = (b) =>
  `await drone.turn(${JSON.stringify(b.getFieldValue('DIR'))}, ${Number(b.getFieldValue('POWER'))}, ${seconds(b, 'SECONDS')});\n`;
js.forBlock.dk_land = (b) => `await drone.land(${Number(b.getFieldValue('SECONDS'))});\n`;
js.forBlock.dk_wait = (b) => `await drone.wait(${seconds(b, 'SECONDS')});\n`;
js.forBlock.dk_battery = () => ['drone.battery()', Order.FUNCTION_CALL];
js.forBlock.dk_say = (b) => `drone.print(${js.valueToCode(b, 'TEXT', Order.NONE) || "''"});\n`;

// Every loop pass yields and checks Stop, so a loop can't freeze the page
// or outlive a kill.
js.INFINITE_LOOP_TRAP = 'await drone.tick();\n';

const num = (n) => ({ shadow: { type: 'math_number', fields: { NUM: n } } });

export const TOOLBOX = {
  kind: 'categoryToolbox',
  contents: [
    {
      kind: 'category', name: 'Drone', colour: String(DRONE_COLOUR),
      contents: [
        { kind: 'block', type: 'dk_arm' },
        { kind: 'block', type: 'dk_takeoff' },
        { kind: 'block', type: 'dk_hover', inputs: { SECONDS: num(2) } },
        { kind: 'block', type: 'dk_move', inputs: { SECONDS: num(1) } },
        { kind: 'block', type: 'dk_turn', inputs: { SECONDS: num(1) } },
        { kind: 'block', type: 'dk_land' },
      ],
    },
    {
      kind: 'category', name: 'Sense', colour: '120',
      contents: [
        { kind: 'block', type: 'dk_wait', inputs: { SECONDS: num(1) } },
        { kind: 'block', type: 'dk_battery' },
        { kind: 'block', type: 'dk_say', inputs: { TEXT: { shadow: { type: 'text', fields: { TEXT: 'hello' } } } } },
      ],
    },
    {
      kind: 'category', name: 'Loops', categorystyle: 'loop_category',
      contents: [
        { kind: 'block', type: 'controls_repeat_ext', inputs: { TIMES: num(4) } },
        { kind: 'block', type: 'controls_whileUntil' },
        { kind: 'block', type: 'controls_for', inputs: { FROM: num(1), TO: num(4), BY: num(1) } },
      ],
    },
    {
      kind: 'category', name: 'Logic', categorystyle: 'logic_category',
      contents: [
        { kind: 'block', type: 'controls_if' },
        { kind: 'block', type: 'logic_compare' },
        { kind: 'block', type: 'logic_operation' },
        { kind: 'block', type: 'logic_boolean' },
      ],
    },
    {
      kind: 'category', name: 'Maths', categorystyle: 'math_category',
      contents: [
        { kind: 'block', type: 'math_number' },
        { kind: 'block', type: 'math_arithmetic' },
        { kind: 'block', type: 'math_random_int', inputs: { FROM: num(1), TO: num(10) } },
      ],
    },
    { kind: 'category', name: 'Text', categorystyle: 'text_category', contents: [{ kind: 'block', type: 'text' }, { kind: 'block', type: 'text_join' }] },
    { kind: 'category', name: 'Variables', categorystyle: 'variable_category', custom: 'VARIABLE' },
  ],
};

// The first program a new user sees.
export const STARTER = {
  blocks: {
    languageVersion: 0,
    blocks: [{
      type: 'dk_arm', x: 24, y: 24,
      next: { block: {
        type: 'dk_takeoff', fields: { THROTTLE: 45, SECONDS: 1 },
        next: { block: {
          type: 'dk_hover', inputs: { SECONDS: num(2) },
          next: { block: { type: 'dk_land', fields: { SECONDS: 2 } } },
        } },
      } },
    }],
  },
};

export function generate(workspace) {
  return js.workspaceToCode(workspace);
}
