// Hover popup for a sea point. Pure formatting; no map or network access.
export const MISSING = '—';

// Forecasts older than this are shown as unknown rather than as current.
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
 * Decide whether values may be shown for a forecast timestamp.
 *
 * A missing timestamp means the age of the forecast is unknown, and unknown
 * forecasts must never be presented as current.
 *
 * Args:
 *   asOf: ISO timestamp string or epoch milliseconds, or undefined.
 *   now: current time in epoch milliseconds.
 * Returns:
 *   true only when asOf parses to a time no older than MAX_AGE_MS and not in
 *   the future; false for absent, unparseable or stale timestamps.
 */
function isUsable(asOf, now) {
  if (asOf === undefined || asOf === null) {
    return false;
  }
  const stamp = typeof asOf === 'number' ? asOf : Date.parse(asOf);
  if (!Number.isFinite(stamp)) {
    return false;
  }
  const age = now - stamp;
  return age >= 0 && age <= MAX_AGE_MS;
}

/**
 * Format wind speed and wave height for one point.
 *
 * Args:
 *   point: object with optional `wind_speed_ms`, `wave_height_m` numbers and
 *     a required `as_of` forecast timestamp.
 *   now: current time in epoch milliseconds, used for forecast age.
 * Returns:
 *   Object with `wind` and `waves` strings; missing or invalid values are an
 *   em dash, never a guessed number. Values without a usable forecast
 *   timestamp are also an em dash.
 */
export function formatPoint(point, now = Date.now()) {
  const source = point && typeof point === 'object' ? point : {};
  const usable = isUsable(source.as_of, now);
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
 * Returns:
 *   Array of two strings: "Wind: X m/s" and "Waves: Y m".
 */
export function popupLines(point, now = Date.now()) {
  const values = formatPoint(point, now);
  return [`Wind: ${values.wind}`, `Waves: ${values.waves}`];
}

/**
 * Render the popup content into a DOM element.
 *
 * Args:
 *   document: DOM document used to create elements.
 *   point: object with optional `wind_speed_ms`, `wave_height_m` and `as_of`.
 *   now: current time in epoch milliseconds.
 * Returns:
 *   A detached element containing one line per measurement.
 */
export function renderPopup(document, point, now = Date.now()) {
  const container = document.createElement('div');
  container.className = 'sea-popup';
  for (const line of popupLines(point, now)) {
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
 * Handle one mousemove event by opening the popup at the hovered point.
 *
 * Args:
 *   state: object with `L`, `map`, `doc`, `lookup`, `minIntervalMs` and the
 *     mutable `lastRun` throttle timestamp.
 *   event: Leaflet mousemove event with `latlng`.
 * Returns:
 *   Nothing; the popup is opened on the map as a side effect.
 */
function handleMouseMove(state, event) {
  const now = Date.now();
  if (now - state.lastRun < state.minIntervalMs) {
    return;
  }
  state.lastRun = now;
  const point = { latitude: event.latlng.lat, longitude: event.latlng.lng };
  const data = safeLookup(state.lookup, point);
  state.L.popup({ className: 'sea-popup-container' })
    .setLatLng(event.latlng)
    .setContent(renderPopup(state.doc, data, now))
    .openOn(state.map);
}

/**
 * Bind a hover popup to a Leaflet map.
 *
 * Args:
 *   L: Leaflet namespace.
 *   map: Leaflet map instance.
 *   lookup: function (point) => data object, or null when data is unknown.
 *   options: optional object with `document` (defaults to global document)
 *     and `minIntervalMs` throttle for mousemove (default 100 ms).
 * Returns:
 *   Object with `dispose()` that removes the hover handler.
 */
export function attachPopup(L, map, lookup, options = {}) {
  const doc = options.document || (typeof document === 'undefined' ? null : document);
  const state = {
    L,
    map,
    doc,
    lookup,
    minIntervalMs: finite(options.minIntervalMs) ? options.minIntervalMs : 100,
    lastRun: -Infinity,
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
