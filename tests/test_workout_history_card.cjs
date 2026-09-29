const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const registry = new Map();
vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../frontend/wger-workout-history-card.js'), 'utf8'), {
  HTMLElement: class {
    attachShadow() {
      this.shadowRoot = { innerHTML: '', querySelector: () => null };
    }
  },
  customElements: { define: (name, cls) => registry.set(name, cls) },
  window: {},
});
const Card = registry.get('wger-workout-history-card');
const FIRST = '01a0e931-733b-7e65-8a4e-f718ec08a900';
const SECOND = '01a0e931-733b-7e65-8a4e-f718ec08a901';

test('shows a selector first, then the selected session and its sets', async () => {
  const card = new Card();
  const requests = [];
  card.setConfig({});
  assert.match(card.shadowRoot.innerHTML, /Cargando entrenos/);
  assert.doesNotMatch(card.shadowRoot.innerHTML, /class="detail"/);
  card.hass = { connection: { sendMessagePromise: async (message) => {
    requests.push(message);
    if (message.type === 'wger/workout_history') return { workouts: [
      { session_id: FIRST, date_start: '2026-09-29T08:00:00Z', workout_name: 'Torso' },
    ] };
    return { workout: {
      workout_name: 'Torso', date_start: '2026-09-29T08:00:00Z', duration: 65,
      totals: { total_exercises: 1, total_sets: 1, total_repetitions: 10, total_volume: 500 },
      exercises: [{ exercise_id: 7, name: 'Press banca', total_repetitions: 10,
        total_volume: 500, max_weight: 50, sets: [{ repetitions: 10, weight: 50, rir: 2, rest: 90 }] }],
      muscle_distribution: [{ muscle: 'Pecho', percentage: 100 }],
    } };
  } } };
  await new Promise(setImmediate);
  assert.match(card.shadowRoot.innerHTML, /Torso/);
  await card._select(FIRST);
  assert.equal(requests[1].session_id, FIRST);
  const html = card.shadowRoot.innerHTML;
  assert.match(html, /Press banca/);
  assert.match(html, /Pecho/);
  assert.match(html, /Descanso/);
  assert.match(html, /1 h 5 min/);
});

test('stale detail responses cannot replace a newer selection', async () => {
  let resolveFirst;
  const card = new Card();
  card.setConfig({});
  card._workouts = [{ session_id: FIRST }, { session_id: SECOND }];
  card._hass = { connection: { sendMessagePromise: (message) =>
    message.session_id === FIRST ? new Promise((resolve) => { resolveFirst = resolve; })
      : Promise.resolve({ workout: { workout_name: 'Segundo', totals: {} } }),
  } };
  const first = card._select(FIRST);
  await card._select(SECOND);
  resolveFirst({ workout: { workout_name: 'Primero', totals: {} } });
  await first;
  assert.match(card.shadowRoot.innerHTML, /Segundo/);
  assert.doesNotMatch(card.shadowRoot.innerHTML, /<h2>Primero<\/h2>/);
});

test('untrusted names are escaped', () => {
  const card = new Card();
  card.setConfig({});
  card._workouts = [{ session_id: 1, workout_name: '<script>x</script>' }];
  card._render();
  assert.match(card.shadowRoot.innerHTML, /&lt;script&gt;/);
  assert.doesNotMatch(card.shadowRoot.innerHTML, /<script>/);
});

test('sections view lets the card grow with the selected workout', () => {
  const card = new Card();
  card.setConfig({});
  assert.equal(card.getGridOptions().rows, undefined);
  card.shadowRoot.querySelector = () => ({ scrollHeight: 1450 });
  assert.equal(card.getCardSize(), 29);
});
