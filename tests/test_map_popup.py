"""Map popup formatting: wind speed and wave height, never guessed values."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / 'frontend' / 'map' / 'popup.mjs'
NODE = shutil.which('node')

# A fresh forecast timestamp so values are treated as current.
FRESH = '2024-01-01T00:00:00Z'
FRESH_MS = 1704067200000

# Runs the ES module in Node and prints the formatted results as JSON.
SCRIPT = """
import { formatPoint, popupLines } from %s;
const cases = JSON.parse(process.argv[1]);
const now = Number(process.argv[2]);
const out = cases.map(point => ({
  point: formatPoint(point, now),
  lines: popupLines(point, now),
}));
process.stdout.write(JSON.stringify(out));
"""

# Renders the popup with a stub document and exercises attachPopup with stubs.
RENDER_SCRIPT = """
import { renderPopup, attachPopup } from %s;
function makeDocument() {
  return {
    createElement() {
      return {
        className: '',
        textContent: '',
        children: [],
        append(child) { this.children.push(child); },
      };
    },
  };
}
const doc = makeDocument();
const now = Number(process.argv[2]);
const element = renderPopup(doc, JSON.parse(process.argv[1]), now);
const rows = element.children.map(row => row.textContent);

const opened = [];
const handlers = {};
const popup = {
  setLatLng(latlng) { this.latlng = latlng; return this; },
  setContent(content) { this.content = content; return this; },
  openOn(map) { opened.push({ latlng: this.latlng, content: this.content }); return this; },
};
const L = { popup: () => popup };
const map = {
  on(name, fn) { handlers[name] = fn; },
  off(name, fn) { if (handlers[name] === fn) { delete handlers[name]; } },
};
const handle = attachPopup(L, map, () => ({
  wind_speed_ms: 3,
  wave_height_m: 2,
  as_of: new Date(Date.now() - 60000).toISOString(),
}), {
  document: doc,
  minIntervalMs: 0,
});
handlers.mousemove({ latlng: { lat: 1, lng: 2 } });
const attachedRows = opened[0].content.children.map(row => row.textContent);
const latlng = opened[0].latlng;
handle.dispose();
const remaining = Object.keys(handlers).length;
process.stdout.write(JSON.stringify({
  className: element.className,
  rows,
  attachedRows,
  latlng,
  remaining,
}));
"""


def run_popup(cases, now=FRESH_MS):
    """Return formatPoint/popupLines output for each case via Node."""
    script = SCRIPT % json.dumps(str(MODULE))
    completed = subprocess.run(
        [NODE, '--input-type=module', '-e', script, json.dumps(cases), str(now)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(completed.stdout)


def run_render(point, now=FRESH_MS):
    """Return renderPopup/attachPopup results for one point via Node."""
    script = RENDER_SCRIPT % json.dumps(str(MODULE))
    completed = subprocess.run(
        [NODE, '--input-type=module', '-e', script, json.dumps(point), str(now)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(completed.stdout)


@unittest.skipIf(NODE is None, 'node is not installed')
class MapPopupTests(unittest.TestCase):
    """Acceptance checks for the hover popup content."""

    def test_wind_and_waves_are_rendered_with_units(self):
        """Present data renders 'Wind: X m/s' and 'Waves: Y m'."""
        [result] = run_popup([
            {'wind_speed_ms': 7.25, 'wave_height_m': 1.5, 'as_of': FRESH},
        ])
        self.assertEqual(result['lines'], ['Wind: 7.3 m/s', 'Waves: 1.5 m'])

    def test_missing_data_renders_em_dash(self):
        """Missing values render an em dash instead of a guessed number."""
        [result] = run_popup([{'as_of': FRESH}])
        self.assertEqual(result['lines'], ['Wind: — m/s', 'Waves: — m'])

    def test_invalid_values_are_not_guessed(self):
        """Null, NaN, strings and missing points never become numbers."""
        cases = [
            {'wind_speed_ms': None, 'wave_height_m': None, 'as_of': FRESH},
            {'wind_speed_ms': 'abc', 'wave_height_m': True, 'as_of': FRESH},
            None,
        ]
        for result in run_popup(cases):
            self.assertEqual(result['lines'], ['Wind: — m/s', 'Waves: — m'])

    def test_zero_is_a_real_measurement(self):
        """Zero wind and zero waves are shown as measured values."""
        [result] = run_popup([
            {'wind_speed_ms': 0, 'wave_height_m': 0, 'as_of': FRESH},
        ])
        self.assertEqual(result['lines'], ['Wind: 0.0 m/s', 'Waves: 0.0 m'])

    def test_partial_data_keeps_known_value(self):
        """A known wind value is shown while missing waves stay an em dash."""
        [result] = run_popup([{'wind_speed_ms': 4.04, 'as_of': FRESH}])
        self.assertEqual(result['lines'], ['Wind: 4.0 m/s', 'Waves: — m'])

    def test_values_without_timestamp_are_not_shown_as_current(self):
        """Wind/wave values without as_of render as em dashes, never as current."""
        cases = [
            {'wind_speed_ms': 9, 'wave_height_m': 3},
            {'wind_speed_ms': 9, 'wave_height_m': 3, 'as_of': None},
        ]
        for result in run_popup(cases):
            self.assertEqual(result['lines'], ['Wind: — m/s', 'Waves: — m'])

    def test_stale_forecast_is_not_shown_as_current(self):
        """Values with an old or unparseable as_of render as em dashes."""
        cases = [
            {'wind_speed_ms': 9, 'wave_height_m': 3, 'as_of': '2000-01-01T00:00:00Z'},
            {'wind_speed_ms': 9, 'wave_height_m': 3, 'as_of': 'not-a-date'},
        ]
        for result in run_popup(cases):
            self.assertEqual(result['lines'], ['Wind: — m/s', 'Waves: — m'])

    def test_render_popup_creates_two_rows(self):
        """renderPopup builds a container with one row per measurement."""
        result = run_render(
            {'wind_speed_ms': 7.25, 'wave_height_m': 1.5, 'as_of': FRESH},
        )
        self.assertEqual(result['className'], 'sea-popup')
        self.assertEqual(result['rows'], ['Wind: 7.3 m/s', 'Waves: 1.5 m'])

    def test_render_popup_missing_data_is_em_dash(self):
        """renderPopup shows em dashes when the lookup returned nothing."""
        result = run_render(None)
        self.assertEqual(result['rows'], ['Wind: — m/s', 'Waves: — m'])

    def test_attach_popup_opens_popup_and_disposes(self):
        """attachPopup opens a popup at the hovered point and can be removed."""
        result = run_render({'wind_speed_ms': 3, 'wave_height_m': 2, 'as_of': FRESH})
        self.assertEqual(result['attachedRows'], ['Wind: 3.0 m/s', 'Waves: 2.0 m'])
        self.assertEqual(result['latlng'], {'lat': 1, 'lng': 2})
        self.assertEqual(result['remaining'], 0)


if __name__ == '__main__':
    unittest.main()
