/**
 * Pure helpers for rendering a departure timeline.
 *
 * No React or other framework dependency: the module only uses the DOM
 * implementation supplied through the container's `ownerDocument`, so it can
 * be exercised with `node --test` and a stub document.
 */

/** Placeholder shown when a departure time is missing or unparseable. */
export const MISSING_TIME = '—';

/** CSS class applied to the timeline list. */
export const TIMELINE_CLASS = 'departure-timeline';

/** CSS class applied to each timeline item. */
export const ITEM_CLASS = 'departure-timeline__item';

/** CSS class applied to the selected timeline item. */
export const SELECTED_CLASS = 'departure-timeline__item--selected';

/**
 * Format a departure time as a local time string.
 *
 * @param {Date|string|number|null|undefined} value Time to format.
 * @param {string} [locale='sv-SE'] Locale passed to `Intl.DateTimeFormat`.
 * @returns {string} Formatted local time, or '—' when the value is missing or
 *   cannot be parsed into a valid date.
 */
export function formatDepartureTime(value, locale = 'sv-SE') {
  if (value === null || value === undefined) {
    return MISSING_TIME;
  }
  const date = value instanceof Date ? value : new Date(value);
  const time = date.getTime();
  if (!Number.isFinite(time)) {
    return MISSING_TIME;
  }
  return new Intl.DateTimeFormat(locale, {
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

/**
 * Return a stable, unique key for a departure.
 *
 * The id is preferred when present; otherwise the index is combined with the
 * departure time so two departures sharing a time still get distinct keys.
 *
 * @param {object|null|undefined} departure Departure record.
 * @param {number} index Position of the departure in the list.
 * @returns {string} Key unique within the rendered list.
 */
export function departureKey(departure, index) {
  const position = Number.isInteger(index) ? index : 0;
  const id = departure ? departure.id : undefined;
  if (id !== null && id !== undefined && id !== '') {
    return `departure-${String(id)}`;
  }
  const time = departure ? departure.time : undefined;
  const stamp = time instanceof Date ? time.getTime() : String(time ?? '');
  return `departure-${position}-${stamp}`;
}

/**
 * Report whether a departure matches the selected id.
 *
 * Matching is by id only; the index is never used, so reordering the list
 * does not change the selection.
 *
 * @param {object|null|undefined} departure Departure record.
 * @param {string|number|null|undefined} selectedId Currently selected id.
 * @returns {boolean} True when the departure id equals the selected id.
 */
export function isDepartureSelected(departure, selectedId) {
  if (!departure || selectedId === null || selectedId === undefined) {
    return false;
  }
  const id = departure.id;
  if (id === null || id === undefined) {
    return false;
  }
  return String(id) === String(selectedId);
}

/**
 * Build the text label for one departure item.
 *
 * @param {object|null|undefined} departure Departure record.
 * @param {string} locale Locale used for the time.
 * @returns {string} Label such as '07:15 Destination'.
 */
export function departureLabel(departure, locale = 'sv-SE') {
  const time = formatDepartureTime(departure ? departure.time : null, locale);
  const destination = departure && departure.destination
    ? String(departure.destination)
    : '';
  return destination ? `${time} ${destination}` : time;
}

/**
 * Render a departure timeline into a container element.
 *
 * Replaces the container's children with a single `<ul>` holding one `<li>`
 * per departure. Clicking an item calls `onSelect(id)` with that departure's
 * id. Elements are created with the container's `ownerDocument`.
 *
 * @param {object} container Element that receives the timeline.
 * @param {Array<object>} departures Departures to render.
 * @param {object} [options] Rendering options.
 * @param {(id: (string|number)) => void} [options.onSelect] Click handler.
 * @param {string|number|null} [options.selectedId] Id to mark as selected.
 * @param {string} [options.locale='sv-SE'] Locale used for times.
 * @returns {object} The created `<ul>` element.
 * @throws {TypeError} When the container has no usable `ownerDocument`.
 */
export function renderTimeline(container, departures, options = {}) {
  if (!container || !container.ownerDocument) {
    throw new TypeError('renderTimeline requires a container with ownerDocument');
  }
  const doc = container.ownerDocument;
  const { onSelect, selectedId = null, locale = 'sv-SE' } = options;
  const list = doc.createElement('ul');
  list.className = TIMELINE_CLASS;

  const items = Array.isArray(departures) ? departures : [];
  items.forEach((departure, index) => {
    const item = doc.createElement('li');
    item.className = ITEM_CLASS;
    item.dataset.key = departureKey(departure, index);
    if (departure && departure.id !== null && departure.id !== undefined) {
      item.dataset.id = String(departure.id);
    }
    if (isDepartureSelected(departure, selectedId)) {
      item.className = `${ITEM_CLASS} ${SELECTED_CLASS}`;
      item.setAttribute('aria-selected', 'true');
    }
    item.textContent = departureLabel(departure, locale);
    if (typeof onSelect === 'function' && departure) {
      item.addEventListener('click', () => onSelect(departure.id));
    }
    list.appendChild(item);
  });

  while (container.firstChild) {
    container.removeChild(container.firstChild);
  }
  container.appendChild(list);
  return list;
}
