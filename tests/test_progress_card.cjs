const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const registry = new Map();
vm.runInNewContext(
  fs.readFileSync(path.join(__dirname, '../frontend/wger-progress-card.js'), 'utf8'),
  {
    HTMLElement: class {
      attachShadow() {
        this.shadowRoot = {
          innerHTML: '',
          appendChild() {},
          querySelectorAll() { return []; },
          querySelector() { return null; },
        };
      }
    },
    customElements: {
      define: (name, cls) => registry.set(name, cls),
      get: (name) => registry.get(name),
    },
    document: { createElement: () => ({}) },
    window: {},
  },
);

const Card = registry.get('wger-progress-card');

test('latest workout uses the last session time when two share a date', () => {
  const card = new Card();
  card.setConfig({});
  card.hass = { states: { 'sensor.workout_progress': { attributes: { workouts: [
    { session_id: 2, date: '2026-09-29', date_start: '2026-09-29T18:00:00Z',
      workout_name: 'Evening workout', total_sets: 3, total_repetitions: 20,
      total_volume: 100 },
    { session_id: 1, date: '2026-09-29', date_start: '2026-09-29T08:00:00Z',
      workout_name: 'Morning workout', total_sets: 3, total_repetitions: 20,
      total_volume: 100 },
  ] } } } };

  assert.match(card.shadowRoot.innerHTML, /class="latest-name">\s*Evening workout/);
});
