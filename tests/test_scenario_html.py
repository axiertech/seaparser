"""Public report export checks, independent of voyage calculations."""
import json
from html.parser import HTMLParser
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import unquote
from unittest.mock import patch

from application.planning import run_plan
from presentation.scenario_html import outcome, render_report, render_reports
from scripts.export_scenario_html import build_demo
from scripts.plan_synthetic import demo_request


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.tags = []
        self.exports = []
        self.feed(source)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        self.tags.append((tag, attrs))
        if tag == 'a' and 'download' in attrs:
            self.exports.append(unquote(attrs['href'].split(',', 1)[1]))


class ScenarioHtmlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = run_plan(demo_request(blocked_direct=True))
        cls.demo = build_demo()

    def test_exact_report_export_and_metrics(self):
        source = render_report(self.raw)
        self.assertEqual(Page(source).exports, [self.raw])
        report = json.loads(self.raw)
        for departure in report['comparison']['departures']:
            for route in departure['routes']['candidates']:
                if route['travel_seconds'] is not None:
                    self.assertIn(f'{route["travel_seconds"]:.2f}'.replace('.', ',')+' s', source)
        self.assertIn('Ingen verifierad kandidatrutt vid denna avgång', source)
        self.assertIn('Andra rutter och avgångstider kan vara möjliga', source)

    def test_demo_distinguishes_evidence_and_is_self_contained(self):
        page = Page(self.demo)
        self.assertEqual(len(page.exports), 5)
        self.assertEqual(len([t for t, _ in page.tags if t == 'svg']), 10)
        for tag, attrs in page.tags:
            self.assertNotIn(tag, ('script', 'iframe', 'object'))
            for key in ('src', 'href'):
                self.assertFalse(attrs.get(key, '').startswith(('http:', 'https:', '//')))
        reports = [json.loads(raw) for raw in page.exports]
        statuses = {r['status'] for report in reports for d in report['comparison']['departures']
                    for r in d['routes']['candidates']}
        self.assertTrue({'arrived', 'blocked', 'weather_limit', 'weather_unverified', 'data_unavailable'} <= statuses)
        for label in ('Konstaterat överskridande', 'Otillräckligt bevis', 'Verifierade modellgränser'):
            self.assertIn(label, self.demo)

    def test_only_certified_arrival_has_verified_badge(self):
        route = {'status': 'arrived', 'weather_segment_status': 'verified',
                 'arrival_weather_status': 'passed_at_arrival'}
        self.assertEqual(outcome(route)[0], 'verified')
        for field, value in (('weather_segment_status', 'incomplete'),
                             ('arrival_weather_status', 'not_checked')):
            self.assertEqual(outcome({**route, field: value})[0], 'unknown')

    def test_text_injection_is_escaped(self):
        report = json.loads(self.raw)
        attack = '<script>alert("x")</script>'
        report['manifest']['dataset_id'] = attack
        source = render_report(json.dumps(report), attack)
        self.assertNotIn(attack, source)
        self.assertIn('&lt;script&gt;', source)
        self.assertNotIn('script', [tag for tag, _ in Page(source).tags])

    def test_rejected_route_has_no_accepted_line(self):
        source = render_report(run_plan(demo_request(scenario='weather-limit')))
        self.assertIn('class="planned"', source)
        self.assertNotIn('class="accepted"', source)

    def test_renderer_uses_existing_report_without_solver(self):
        with patch('application.planning.run_plan', side_effect=AssertionError('solver invoked')):
            self.assertEqual(Page(render_report(self.raw)).exports, [self.raw])

    def test_invalid_reports_and_limits(self):
        for raw in ('{}', 'null', '{"bad":NaN}', self.raw.replace('"schema_version":1', '"schema_version":99')):
            with self.subTest(raw=raw[:20]), self.assertRaises(ValueError):
                render_report(raw)
        with self.assertRaises(ValueError):
            render_reports([])
        with self.assertRaises(ValueError):
            render_reports([('test', self.raw)] * 11)

    def test_cli_exports_existing_report_exactly(self):
        with tempfile.TemporaryDirectory() as folder:
            input_file = Path(folder)/'report.json'
            output_file = Path(folder)/'index.html'
            input_file.write_text(self.raw, encoding='utf-8')
            completed = subprocess.run([sys.executable, '-B', '-m', 'scripts.export_scenario_html',
                                        '--report', str(input_file), '--output', str(output_file)],
                                       capture_output=True, text=True, check=True)
            self.assertIn('HTML-visning genererad', completed.stdout)
            self.assertEqual(Page(output_file.read_text()).exports, [self.raw])
