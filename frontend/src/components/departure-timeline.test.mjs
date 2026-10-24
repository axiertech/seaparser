/**
 * Tests for the pure departure timeline helpers.
 *
 * Run with: node --test frontend/src/components/departure-timeline.test.mjs
 */
import test from 'node:test';
import assert from 'node:assert/strict';

import {
  MISSING_TIME,
  departureKey,
  departureLabel,
  formatDepartureTime,
  isDepartureSelected,
  renderTimeline,
} from './departure-timeline.mjs';

/**
 * Create a minimal DOM stub with the subset of the API the module uses.
 *
 * @returns {object} Stub document with a `createElement` factory.
 */
function makeDocument() {
  function createElement(tagName) {
    const element = {
      tagName: tagName.toUpperCase(),
      className: '',
      textContent: '',
      dataset: {},
      attributes: {},
      children: [],
      listeners: {},
      firstChild: null,
      setAttribute(name, value) {
        this.attributes[name] = value;
      },
      getAttribute(name) {
        return this.attributes[name];
      },
      addEventListener(name, handler) {
        this.listeners[name] = handler;
      },
      appendChild(child) {
        this.children.push(child);
        this.firstChild = this.children[0];
        return child;
      },
      removeChild(child) {
        this.children = this.children.filter((entry) => entry !== child);
        this.firstChild = this.children[0] || null;
        return child;
      },
      click() {
        if (this.listeners.click) {
          this.listeners.click({ target: this });
        }
      },
    };
    return element;
  }
  return { createElement };
}

/**
 * Create a container element bound to a fresh stub document.
 *
 * @returns {object} Container element.
 */
function makeContainer() {
  const doc = makeDocument();
  const container = doc.createElement('div');
  container.ownerDocument = doc;
  return container;
}

test('formatDepartureTime returns an em dash for null', () => {
  assert.equal(formatDepartureTime(null), MISSING_TIME);
  assert.equal(MISSING_TIME, '—');
});

test('formatDepartureTime returns an em dash for undefined', () => {
  assert.equal(formatDepartureTime(undefined), '—');
});

test('formatDepartureTime returns an em dash for an invalid date', () => {
  assert.equal(formatDepartureTime(new Date('invalid')), '—');
  assert.equal(formatDepartureTime('not-a-date'), '—');
});

test('formatDepartureTime formats a valid date as local time', () => {
  const value = new Date(2024, 0, 1, 7, 5, 0);
  assert.equal(formatDepartureTime(value), '07:05');
});

test('formatDepartureTime honours the locale argument', () => {
  const value = new Date(2024, 0, 1, 13, 30, 0);
  const formatted = formatDepartureTime(value, 'en-GB');
  assert.match(formatted, /13:30/);
});

test('departureKey is unique for departures sharing a time', () => {
  const time = new Date(2024, 0, 1, 8, 0, 0);
  const first = departureKey({ time }, 0);
  const second = departureKey({ time }, 1);
  assert.notEqual(first, second);
});

test('departureKey is stable for the same input', () => {
  const departure = { id: 'abc', time: new Date(2024, 0, 1, 8, 0, 0) };
  assert.equal(departureKey(departure, 0), departureKey(departure, 0));
});

test('departureKey prefers the id when present', () => {
  assert.equal(departureKey({ id: 'abc' }, 3), 'departure-abc');
});

test('isDepartureSelected matches by id, not index', () => {
  const departures = [
    { id: 'a', time: new Date(2024, 0, 1, 8, 0, 0) },
    { id: 'b', time: new Date(2024, 0, 1, 9, 0, 0) },
  ];
  assert.equal(isDepartureSelected(departures[1], 'b'), true);
  assert.equal(isDepartureSelected(departures[0], 'b'), false);
  assert.equal(isDepartureSelected(departures[0], 0), false);
});

test('isDepartureSelected is false for missing ids', () => {
  assert.equal(isDepartureSelected(null, 'a'), false);
  assert.equal(isDepartureSelected({}, 'a'), false);
  assert.equal(isDepartureSelected({ id: 'a' }, null), false);
});

test('departureLabel combines time and destination', () => {
  const departure = { time: new Date(2024, 0, 1, 7, 15, 0), destination: 'Skagen' };
  assert.equal(departureLabel(departure), '07:15 Skagen');
  assert.equal(departureLabel({ time: null }), '—');
});

test('renderTimeline builds one list item per departure', () => {
  const container = makeContainer();
  const departures = [
    { id: 'a', time: new Date(2024, 0, 1, 8, 0, 0), destination: 'Oslo' },
    { id: 'b', time: new Date(2024, 0, 1, 8, 0, 0), destination: 'Kiel' },
  ];
  const list = renderTimeline(container, departures, { onSelect: () => {} });

  assert.equal(list.tagName, 'UL');
  assert.equal(container.children.length, 1);
  assert.equal(container.children[0], list);
  assert.equal(list.children.length, 2);
  assert.equal(list.children[0].tagName, 'LI');
  assert.equal(list.children[0].textContent, '08:00 Oslo');
  assert.equal(list.children[1].textContent, '08:00 Kiel');
});

test('renderTimeline gives distinct keys to departures with the same time', () => {
  const container = makeContainer();
  const time = new Date(2024, 0, 1, 8, 0, 0);
  const list = renderTimeline(container, [{ time }, { time }], {});
  const keys = list.children.map((item) => item.dataset.key);
  assert.equal(new Set(keys).size, 2);
});

test('renderTimeline calls onSelect with the clicked id', () => {
  const container = makeContainer();
  const selected = [];
  const list = renderTimeline(
    container,
    [{ id: 'a', time: new Date(2024, 0, 1, 8, 0, 0) },
      { id: 'b', time: new Date(2024, 0, 1, 9, 0, 0) }],
    { onSelect: (id) => selected.push(id) },
  );

  list.children[1].click();
  list.children[0].click();
  assert.deepEqual(selected, ['b', 'a']);
});

test('renderTimeline marks the selected item by id', () => {
  const container = makeContainer();
  const list = renderTimeline(
    container,
    [{ id: 'a' }, { id: 'b' }],
    { selectedId: 'b' },
  );
  assert.equal(list.children[0].getAttribute('aria-selected'), undefined);
  assert.equal(list.children[1].getAttribute('aria-selected'), 'true');
  assert.match(list.children[1].className, /selected/);
});

test('renderTimeline replaces previous content', () => {
  const container = makeContainer();
  renderTimeline(container, [{ id: 'a' }], {});
  const list = renderTimeline(container, [{ id: 'b' }], {});
  assert.equal(container.children.length, 1);
  assert.equal(container.children[0], list);
  assert.equal(list.children.length, 1);
});

test('renderTimeline requires a container with ownerDocument', () => {
  assert.throws(() => renderTimeline(null, [], {}), TypeError);
  assert.throws(() => renderTimeline({}, [], {}), TypeError);
});
