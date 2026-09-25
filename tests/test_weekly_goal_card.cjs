// Run with: node --test tests/test_weekly_goal_card.cjs
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const registry = new Map();
const context = {
  HTMLElement: class { attachShadow() { this.shadowRoot = { innerHTML: '' }; } },
  customElements: { get: (name) => registry.get(name), define: (name, cls) => registry.set(name, cls) },
  window: {},
};
vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../frontend/wger-weekly-goal-card.js'), 'utf8'), context);
const Card = registry.get('wger-weekly-goal-card');
function render(completed, target, state = '66.7') {
  const card = new Card();
  card.setConfig({ title: '<img src=x onerror=alert(1)>' });
  card.hass = { states: { 'sensor.weekly_goal_progress': {
    state, attributes: { completed, target, week_start: '2026-09-21', week_end: '2026-09-27' },
  } } };
  return card.shadowRoot.innerHTML;
}
test('partial goal shows remaining sessions and escapes custom titles', () => {
  const html = render(2, 3);
  assert.match(html, /Te queda 1 sesión/);
  assert.match(html, /aria-valuenow="67"/);
  assert.match(html, /&lt;img/);
  assert.doesNotMatch(html, /<img/);
});
test('exceeded goal keeps actual count and caps progress', () => {
  const html = render(4, 3, '100');
  assert.match(html, /<strong>4<\/strong>/);
  assert.match(html, /Objetivo cumplido/);
  assert.match(html, /width:100%/);
});
test('unavailable data never appears as a zero or completed goal', () => {
  const html = render(4, 3, 'unavailable');
  assert.match(html, /Datos no disponibles/);
  assert.doesNotMatch(html, /role="progressbar"/);
});
test('missing entity identifies configuration problem', () => {
  const card = new Card();
  card.setConfig({ entity: 'sensor.other_goal' });
  card.hass = { states: {} };
  assert.match(card.shadowRoot.innerHTML, /No se encuentra sensor.other_goal/);
});
