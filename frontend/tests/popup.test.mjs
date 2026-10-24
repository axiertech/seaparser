// Unit tests for frontend/map/popup.mjs: document handling, forecast age
// override and popup reuse. No jsdom, no network, no real Leaflet.
import assert from 'node:assert/strict';
import test from 'node:test';

import {
  MAX_AGE_MS,
  attachPopup,
  formatPoint,
  popupLines,
  renderPopup,
} from '../map/popup.mjs';

const NOW = 1704067200000; // 2024-01-01T00:00:00Z

/**
 * Build a minimal document stub that records created elements.
 *
 * Returns:
 *   Object with `createElement()` and the list of created elements.
 */
function makeDocument() {
  const created = [];
  return {
    created,
    createElement() {
      const element = {
        className: '',
        textContent: '',
        children: [],
        append(child) {
          this.children.push(child);
        },
      };
      created.push(element);
      return element;
    },
  };
}

/**
 * Build a Leaflet stub that counts popup instances and records calls.
 *
 * Returns:
 *   Object with `L`, `map`, `handlers`, `popups` and `opened` records.
 */
function makeLeaflet() {
  const popups = [];
  const opened = [];
  const handlers = {};
  const L = {
    popup(options) {
      const instance = {
        options,
        latlng: null,
        content: null,
        setLatLng(latlng) {
          this.latlng = latlng;
          return this;
        },
        setContent(content) {
          this.content = content;
          return this;
        },
        openOn(map) {
          opened.push({ instance: this, map });
          return this;
        },
      };
      popups.push(instance);
      return instance;
    },
  };
  const map = {
    on(name, fn) {
      handlers[name] = fn;
    },
    off(name, fn) {
      if (handlers[name] === fn) {
        delete handlers[name];
      }
    },
  };
  return { L, map, handlers, popups, opened };
}

/**
 * Return the text rows of a rendered popup container.
 *
 * Args:
 *   container: element produced by renderPopup.
 * Returns:
 *   Array of row text strings.
 */
function rowsOf(container) {
  return container.children.map(row => row.textContent);
}

test('attachPopup throws a clear error when no document exists', () => {
  const { L, map, handlers } = makeLeaflet();
  assert.throws(
    () => attachPopup(L, map, () => null, { document: null }),
    /attachPopup: no document available/,
  );
  // Nothing was bound, so no handler is left behind on the map.
  assert.deepEqual(Object.keys(handlers), []);
});

test('attachPopup rejects a document without createElement', () => {
  const { L, map } = makeLeaflet();
  assert.throws(
    () => attachPopup(L, map, () => null, { document: {} }),
    /no document available/,
  );
});

test('MAX_AGE_MS default is six hours', () => {
  assert.equal(MAX_AGE_MS, 6 * 60 * 60 * 1000);
});

test('a forecast older than MAX_AGE_MS is shown as unknown', () => {
  const point = {
    wind_speed_ms: 5,
    wave_height_m: 1,
    as_of: new Date(NOW - MAX_AGE_MS - 1000).toISOString(),
  };
  assert.deepEqual(popupLines(point, NOW), ['Wind: — m/s', 'Waves: — m']);
});

test('a supplied maxAgeMs override is honoured', () => {
  const point = {
    wind_speed_ms: 5,
    wave_height_m: 1,
    as_of: new Date(NOW - 2 * 60 * 60 * 1000).toISOString(), // 2 h old
  };
  // Default 6 h window accepts it.
  assert.deepEqual(popupLines(point, NOW), ['Wind: 5.0 m/s', 'Waves: 1.0 m']);
  // A 1 h override rejects it.
  assert.deepEqual(
    popupLines(point, NOW, 60 * 60 * 1000),
    ['Wind: — m/s', 'Waves: — m'],
  );
  // A 3 h override accepts it again.
  assert.deepEqual(
    formatPoint(point, NOW, 3 * 60 * 60 * 1000),
    { wind: '5.0 m/s', waves: '1.0 m' },
  );
});

test('an override can widen the window beyond MAX_AGE_MS', () => {
  const point = {
    wind_speed_ms: 4,
    wave_height_m: 2,
    as_of: new Date(NOW - 10 * 60 * 60 * 1000).toISOString(), // 10 h old
  };
  assert.deepEqual(popupLines(point, NOW), ['Wind: — m/s', 'Waves: — m']);
  assert.deepEqual(
    popupLines(point, NOW, 12 * 60 * 60 * 1000),
    ['Wind: 4.0 m/s', 'Waves: 2.0 m'],
  );
});

test('an invalid maxAgeMs falls back to MAX_AGE_MS', () => {
  const point = {
    wind_speed_ms: 4,
    wave_height_m: 2,
    as_of: new Date(NOW - 60 * 60 * 1000).toISOString(),
  };
  for (const bad of [undefined, null, NaN, -1, 'soon']) {
    assert.deepEqual(
      popupLines(point, NOW, bad),
      ['Wind: 4.0 m/s', 'Waves: 2.0 m'],
      `maxAgeMs=${String(bad)} should fall back to the default`,
    );
  }
});

test('renderPopup forwards the maxAgeMs override', () => {
  const doc = makeDocument();
  const point = {
    wind_speed_ms: 4,
    wave_height_m: 2,
    as_of: new Date(NOW - 2 * 60 * 60 * 1000).toISOString(),
  };
  assert.deepEqual(rowsOf(renderPopup(doc, point, NOW)), [
    'Wind: 4.0 m/s',
    'Waves: 2.0 m',
  ]);
  assert.deepEqual(rowsOf(renderPopup(doc, point, NOW, 60 * 60 * 1000)), [
    'Wind: — m/s',
    'Waves: — m',
  ]);
});

test('repeated mousemove reuses one popup instance', () => {
  const doc = makeDocument();
  const { L, map, handlers, popups, opened } = makeLeaflet();
  const handle = attachPopup(L, map, () => ({ as_of: new Date().toISOString() }), {
    document: doc,
    minIntervalMs: 0,
  });

  handlers.mousemove({ latlng: { lat: 1, lng: 2 } });
  handlers.mousemove({ latlng: { lat: 3, lng: 4 } });
  handlers.mousemove({ latlng: { lat: 5, lng: 6 } });

  assert.equal(popups.length, 1, 'only one Leaflet popup is created');
  assert.equal(opened.length, 1, 'the popup is opened once');
  assert.deepEqual(popups[0].latlng, { lat: 5, lng: 6 });
  assert.deepEqual(rowsOf(popups[0].content), ['Wind: — m/s', 'Waves: — m']);

  handle.dispose();
  assert.deepEqual(Object.keys(handlers), []);
});

test('the reused popup gets fresh content on each move', () => {
  const doc = makeDocument();
  const { L, map, handlers, popups } = makeLeaflet();
  const points = [
    { wind_speed_ms: 1, wave_height_m: 0.5, as_of: new Date().toISOString() },
    { wind_speed_ms: 7, wave_height_m: 2.5, as_of: new Date().toISOString() },
  ];
  let index = 0;
  attachPopup(L, map, () => points[index++], { document: doc, minIntervalMs: 0 });

  handlers.mousemove({ latlng: { lat: 0, lng: 0 } });
  const first = rowsOf(popups[0].content);
  handlers.mousemove({ latlng: { lat: 1, lng: 1 } });
  const second = rowsOf(popups[0].content);

  assert.equal(popups.length, 1);
  assert.deepEqual(first, ['Wind: 1.0 m/s', 'Waves: 0.5 m']);
  assert.deepEqual(second, ['Wind: 7.0 m/s', 'Waves: 2.5 m']);
});

test('attachPopup forwards its maxAgeMs option to the popup content', () => {
  const doc = makeDocument();
  const { L, map, handlers, popups } = makeLeaflet();
  const point = {
    wind_speed_ms: 6,
    wave_height_m: 1.5,
    as_of: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
  };
  attachPopup(L, map, () => point, {
    document: doc,
    minIntervalMs: 0,
    maxAgeMs: 60 * 60 * 1000,
  });
  handlers.mousemove({ latlng: { lat: 1, lng: 1 } });
  assert.deepEqual(rowsOf(popups[0].content), ['Wind: — m/s', 'Waves: — m']);
});
