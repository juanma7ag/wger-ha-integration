const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const registry = new Map();
vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../frontend/wger-consistency-card.js'), 'utf8'), {
  HTMLElement: class { attachShadow() { this.shadowRoot = { innerHTML: '' }; } },
  customElements: { get: (name) => registry.get(name), define: (name, cls) => registry.set(name, cls) },
  window: {},
});
const Card = registry.get('wger-consistency-card');
const base = {
  history_complete: true, current_streak: 2, best_streak: 4, target: 3, remaining: 2,
  history_weeks: 52, current_week_achieved: false,
  weeks: ['achieved', 'missed', 'in_progress'].map((status, i) => ({
    status, week_start: '2026-09-21', week_end: '2026-09-27', completed: i, target: 3,
    is_current: i === 2,
  })),
};
function render(attributes, state = '2') {
  const card = new Card();
  card.setConfig({ title: '<script>bad()</script>' });
  card.hass = { states: { 'sensor.weekly_streak': { state, attributes } } };
  return card.shadowRoot.innerHTML;
}
test('open week preserves streak and displays three distinct statuses', () => {
  const html = render(base);
  assert.match(html, /Tu racha sigue viva/);
  assert.match(html, /Faltan 2 sesiones/);
  assert.match(html, /class="week achieved/);
  assert.match(html, /class="week missed/);
  assert.match(html, /class="week in_progress current/);
  assert.match(html, /&lt;script&gt;/);
  assert.doesNotMatch(html, /<script>/);
});
test('current achievement and bounded streak are explicit', () => {
  const html = render({ ...base, current_week_achieved: true, current_streak: 52, streak_at_least: true });
  assert.match(html, /52\+/);
  assert.match(html, /Esta semana ya suma/);
  assert.match(html, /antes del período consultado/);
});
test('incomplete history does not render an invented zero streak', () => {
  const html = render({ history_complete: false }, 'unknown');
  assert.match(html, /historial recibido está incompleto/);
  assert.doesNotMatch(html, /class="metrics"/);
});
test('unavailable entities show no stale streak', () => {
  const html = render(base, 'unavailable');
  assert.match(html, /Datos no disponibles/);
  assert.doesNotMatch(html, /class="weeks"/);
});
test('missing entity and empty history are distinct', () => {
  const card = new Card();
  card.setConfig({ entity: 'sensor.missing' });
  card.hass = { states: {} };
  assert.match(card.shadowRoot.innerHTML, /No se encuentra sensor.missing/);
  assert.match(render({ ...base, current_streak: 0, best_streak: 0 }), /iniciar una racha/);
});
