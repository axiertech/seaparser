// Hover popup for a sea point. Pure formatting; no map or network access.
export const MISSING = '—';

// Default maximum forecast age: 6 hours.
//
// Why 6 hours: the popup is a planning aid, not a live instrument. A forecast
// issued more than six hours ago no longer describes the wind and waves at the
// hovered point well enough, so it must be shown as unknown rather than as
// current (AGENTS.md: unknown or old forecasts must never be treated as safe).
// Six hours is also the shortest common forecast cycle for the weather
// products SeaParser plans to consume, so an older value means at least one
// newer model run should already have been available.
// Callers that need another window pass `maxAgeMs` to `formatPoint`,
// `popupLines`, `renderPopup` or `attachPopup`.
export const MAX_AGE_MS = 6 * 60 * 60 * 1000;

/**
 * Return true when value is a finite number.
 *
 * Args:
 *   value: any value.
 * Returns:
 *   true only for numbers that are not NaN or infinite.
 */
function finite(value) {
  return typeof value === 'number' && Number.isFinite(value);
}

/**
 * Format a measurement with its unit.
 *
 * Args:
 *   value: number or anything else.
 *   unit: unit suffix, e.g. 'm/s'.
 *   digits: number of decimals.
 * Returns:
 *   "X unit" for finite numbers, otherwise "— unit".
 */
function format(value, unit, digits) {
  return `${finite(value) ? value.toFixed(digits) : MISSING} ${unit}`;
}

/**
 * Resolve the maximum forecast age, falling back to MAX_AGE_MS.
 *
 * Args:
 *   maxAgeMs: caller-supplied override, or undefined/null.
 * Returns:
 *   The override when it is a finite, non-negative number, else MAX_AGE_MS.
 */
function resolveMaxAge(maxAgeMs) {
  return finite(maxAgeMs) && maxAgeMs >= 0 ? maxAgeMs : MAX_AGE_MS;
}

/**
 * Decide whether values may be shown for a forecast timestamp.
 *
 * A missing timestamp means the age of the forecast is unknown, and unknown
 * forecasts must never be presented as current.
 *
 * Args:
 *   asOf: ISO timestamp string or epoch milliseconds, or undefined.
 *   now: current time in epoch milliseconds.
 *   maxAgeMs: maximum accepted age in milliseconds (default MAX_AGE_MS).
 * Returns:
 *   true only when asOf parses to a time no older than maxAgeMs and not in
 *   the future; false for absent, unparseable or stale timestamps.
 */
function isUsable(asOf, now, maxAgeMs = MAX_AGE_MS) {
  if (asOf === undefined || asOf === null) {
    return false;
  }
  const stamp = typeof asOf === 'number' ? asOf : Date.parse(asOf);
  if (!Number.isFinite(stamp)) {
    return false;
  }
  const age = now - stamp;
  return age >= 0 && age <= resolveMaxAge(maxAgeMs);
}

/**
 * Format wind speed and wave height for one point.
 *
 * Args:
 *   point: object with optional `wind_speed_ms`, `wave_height_m` numbers and
 *     a required `as_of` forecast timestamp.
 *   now: current time in epoch milliseconds, used for forecast age.
 *   maxAgeMs: optional maximum accepted forecast age in milliseconds;
 *     defaults to MAX_AGE_MS.
 * Returns:
 *   Object with `wind` and `waves` strings; missing or invalid values are an
 *   em dash, never a guessed number. Values without a usable forecast
 *   timestamp are also an em dash.
 */
export function formatPoint(point, now = Date.now(), maxAgeMs = MAX_AGE_MS) {
  const source = point && typeof point === 'object' ? point : {};
  const usable = isUsable(source.as_of, now, maxAgeMs);
  return {
    wind: format(usable ? source.wind_speed_ms : undefined, 'm/s', 1),
    waves: format(usable ? source.wave_height_m : undefined, 'm', 1),
  };
}

/**
 * Build the popup text lines for a point.
 *
 * Args:
 *   point: object with optional `wind_speed_ms`, `wave_height_m` and `as_of`.
 *   now: current time in epoch milliseconds.
 *   maxAgeMs: optional maximum accepted forecast age in milliseconds;
 *     defaults to MAX_AGE_MS.
 * Returns:
 *   Array of two strings: "Wind: X m/s" and "Waves: Y m".
 */
export function popupLines(point, now = Date.now(), maxAgeMs = MAX_AGE_MS) {
  const values = formatPoint(point, now, maxAgeMs);
  return [`Wind: ${values.wind}`, `Waves: ${values.waves}`];
}

/**
 * Render the popup content into a DOM element.
 *
 * Args:
 *   document: DOM document used to create elements.
 *   point: object with optional `wind_speed_ms`, `wave_height_m` and `as_of`.
 *   now: current time in epoch milliseconds.
 *   maxAgeMs: optional maximum accepted forecast age in milliseconds;
 *     defaults to MAX_AGE_MS.
 * Returns:
 *   A detached element containing one line per measurement.
 */
export function renderPopup(document, point, now = Date.now(), maxAgeMs = MAX_AGE_MS) {
  const container = document.createElement('div');
  container.className = 'sea-popup';
  for (const line of popupLines(point, now, maxAgeMs)) {
    const row = document.createElement('div');
    row.className = 'sea-popup-row';
    row.textContent = line;
    container.append(row);
  }
  return container;
}

/**
 * Look up data for a hovered point without letting lookup errors escape.
 *
 * Args:
 *   lookup: function (point) => data object, or null when data is unknown.
 *   point: object with `latitude` and `longitude`.
 * Returns:
 *   The lookup result, or null when lookup is not a function or throws.
 */
function safeLookup(lookup, point) {
  try {
    return typeof lookup === 'function' ? lookup(point) : null;
  } catch {
    // A failing lookup means unknown data; the popup then shows em dashes.
    return null;
  }
}

/**
 * Create the single Leaflet popup reused for every mousemove.
 *
 * Args:
 *   L: Leaflet namespace.
 *   map: Leaflet map instance.
 * Returns:
 *   A detached popup instance; the caller opens it once content is set.
 */
function createPopup(L, map) {
  return L.popup({ className: 'sea-popup-container' });
}

/**
 * Handle one mousemove event by moving and refilling the shared popup.
 *
 * The same popup instance is reused for every move: creating a new popup per
 * mousemove leaks Leaflet layers and makes the popup flicker.
 *
 * Args:
 *   state: object with `L`, `map`, `doc`, `lookup`, `minIntervalMs`,
 *     `maxAgeMs`, the mutable `lastRun` throttle timestamp and the mutable
 *     `popup` instance (created lazily on the first accepted move).
 *   event: Leaflet mousemove event with `latlng`.
 * Returns:
 *   Nothing; the popup is moved and refilled as a side effect.
 */
function handleMouseMove(state, event) {
  const now = Date.now();
  if (now - state.lastRun < state.minIntervalMs) {
    return;
  }
  state.lastRun = now;
  const point = { latitude: event.latlng.lat, longitude: event.latlng.lng };
  const data = safeLookup(state.lookup, point);
  if (!state.popup) {
    state.popup = createPopup(state.L, state.map);
    state.popup
      .setLatLng(event.latlng)
      .setContent(renderPopup(state.doc, data, now, state.maxAgeMs))
      .openOn(state.map);
  } else {
    state.popup
      .setLatLng(event.latlng)
      .setContent(renderPopup(state.doc, data, now, state.maxAgeMs));
  }
}

/**
 * Resolve the document used to build popup content.
 *
 * Args:
 *   options: object that may carry a `document`.
 * Returns:
 *   The supplied document, or the global document when one exists.
 * Raises:
 *   Error when no document is available; silently rendering nothing would
 *   hide a wiring bug.
 */
function resolveDocument(options) {
  const doc = options.document || (typeof document === 'undefined' ? null : document);
  if (!doc || typeof doc.createElement !== 'function') {
    throw new Error(
      'attachPopup: no document available; pass options.document or run in a browser',
    );
  }
  return doc;
}

/**
 * Bind a hover popup to a Leaflet map.
 *
 * Args:
 *   L: Leaflet namespace.
 *   map: Leaflet map instance.
 *   lookup: function (point) => data object, or null when data is unknown.
 *   options: optional object with `document` (defaults to global document),
 *     `minIntervalMs` throttle for mousemove (default 100 ms) and `maxAgeMs`
 *     maximum accepted forecast age (default MAX_AGE_MS).
 * Returns:
 *   Object with `dispose()` that removes the hover handler.
 * Raises:
 *   Error when no usable document is available.
 */
export function attachPopup(L, map, lookup, options = {}) {
  const doc = resolveDocument(options);
  const state = {
    L,
    map,
    doc,
    lookup,
    minIntervalMs: finite(options.minIntervalMs) ? options.minIntervalMs : 100,
    maxAgeMs: resolveMaxAge(options.maxAgeMs),
    lastRun: -Infinity,
    popup: null,
  };
  const handler = event => handleMouseMove(state, event);
  map.on('mousemove', handler);
  return {
    /** Remove the mousemove handler from the map. */
    dispose() {
      map.off('mousemove', handler);
    },
  };
}
