const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const registry = new Map();
vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../frontend/wger-comparison-card.js'), 'utf8'), {
  HTMLElement: class { attachShadow() { this.shadowRoot = { innerHTML: '' }; } },
  customElements: { get: (name) => registry.get(name), define: (name, cls) => registry.set(name, cls) },
  window: {},
});
const Card = registry.get('wger-comparison-card');
const data = {
  current: { date_start: '2026-09-25T00:30:00+02:00' },
  previous: { date_start: '2026-09-18T10:00:00+02:00' },
  routine_name: '<img src=x onerror=alert(1)>',
  metrics: {
    sets: { current: 4, previous: 3, delta: 1, percent: 33.3, unit: 'series' },
    repetitions: { current: 40, previous: 30, delta: 10, percent: 33.3, unit: 'reps' },
    volume: { current: 0, previous: 0, delta: 0, percent: null, unit: 'kg·reps' },
    duration: { current: 45, previous: 60, delta: -15, percent: -25, unit: 'min' },
  },
};
function render(attributes = data, state = 'ready') {
  const card = new Card();
  card.setConfig({});
  card.hass = { states: { 'sensor.workout_comparison': { state, attributes } } };
  return card.shadowRoot.innerHTML;
}
test('signed differences are neutral and routine names are escaped', () => {
  const html = render();
  assert.match(html, /\+1 series/);
  assert.match(html, /-15 min \(-25 %\)/);
  assert.match(html, /Sin cambio/);
  assert.match(html, /&lt;img/);
  assert.doesNotMatch(html, /<img/);
  assert.match(html, /25 sept/);
});
test('unsupported metrics show a dash instead of a fake zero', () => {
  const html = render({ ...data, volume_comparable: false,
    metrics: { volume: { current: null, previous: 500, delta: null, percent: null, unit: 'kg·reps' } } });
  assert.match(html, /No comparable/);
  assert.match(html, /<strong>—/);
  assert.match(html, /peso corporal/);
});
test('changed exercise selection is explained', () => {
  assert.match(render({ ...data, exercise_selection_changed: true }), /ejercicios registrados difieren/);
});
test('first session and incomplete records show distinct empty states', () => {
  assert.match(render({}, 'no_previous'), /primera sesión/);
  assert.match(render({}, 'incomplete_history'), /registros recibidos están incompletos/);
  assert.match(render({}, 'no_day'), /día de rutina asociado/);
});
test('unavailable or missing entity never shows a stale comparison', () => {
  const html = render(data, 'unavailable');
  assert.match(html, /Datos no disponibles/);
  assert.doesNotMatch(html, /class="metrics"/);
  const card = new Card();
  card.setConfig({ entity: 'sensor.missing' });
  card.hass = { states: {} };
  assert.match(card.shadowRoot.innerHTML, /No se encuentra sensor.missing/);
});
