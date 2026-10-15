// Run with: node tests/test_frontend.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'static/index.html'), 'utf8');
const elements = new Map();
let selected = 'pipe';
let nextTick;
const sharedLabel = {textContent: ''};
const sharedCells = Array.from({length: 4}, () => ({textContent: ''}));
const queueBuffer = {dataset: {}};
const classes = () => {
  const values = new Set();
  return { add: (v) => values.add(v), remove: (v) => values.delete(v),
    contains: (v) => values.has(v), toggle: () => {} };
};
function element(id) {
  assert.ok(html.includes(`id="${id}"`), `Missing HTML element ${id}`);
  if (!elements.has(id)) elements.set(id, {dataset: {}, classList: classes(), textContent: '', innerHTML: ''});
  return elements.get(id);
}
const context = vm.createContext({
  document: {
    querySelector: (selector) => selector === 'input[name="method"]:checked'
      ? {value: selected} : selector === '.shared-region em' ? sharedLabel : selector === '.queue-buffer' ? queueBuffer : element(selector.slice(1)),
    querySelectorAll: (selector) => selector === '.shared-region i' ? sharedCells : [],
  },
  setInterval: (callback) => { nextTick = callback; return 1; },
  clearInterval: () => {},
});
const script = fs.readFileSync(path.join(root, 'static/app.js'), 'utf8');
vm.runInContext(script.replace(/\binit\(\);\s*$/, ''), context);
const visuals = new Set();
for (const method of ['pipe', 'queue', 'shared_memory', 'socket']) {
  selected = method;
  vm.runInContext('updateMethod()', context);
  assert.equal(element('topology').dataset.method, method);
  assert.equal(element('metric-rate').textContent, '—');
  visuals.add(element('topology').innerHTML);
  assert.ok(element('topology').innerHTML.includes('ipc-scene'));
  assert.match(element('mechanism-step').textContent, /^1 \/ 3/);
  nextTick();
  assert.match(element('mechanism-step').textContent, /^2 \/ 3/);
  nextTick();
  assert.match(element('mechanism-step').textContent, /^3 \/ 3/);
  if (method === 'shared_memory') {
    assert.ok(sharedCells.every((cell) => cell.textContent === '53'));
    assert.match(sharedLabel.textContent, /^consumed/);
  }
  nextTick();
  assert.equal(element('topology').classList.contains('explaining'), false);
  vm.runInContext(`playMechanism('${method}')`, context);
  assert.match(element('mechanism-step').textContent, /^1 \/ 3/);
}
assert.equal(visuals.size, 4, 'Each mechanism must render a different visualization');
console.log('PASS: four distinct visualizations, phase transitions, replay and stale-metric reset');
