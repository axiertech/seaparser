"""Full-land native search, finite configuration and frozen result regressions."""
import json
from pathlib import Path
import unittest
from pydantic import ValidationError
from api.models import PlanInput
from application.geographic_plan import calculate_geographic
from infrastructure.land import load_land
from prototype.model import Vector
from prototype.auto_routing import generate_routes,SearchPolicy
from scripts.audit_native_candidates import CONFIG,payload

ROOT=Path(__file__).resolve().parents[1]


class NativeCandidateBudgetTests(unittest.TestCase):
    def test_finite_graph_retains_all_land_and_known_direct_length(self):
        snapshot=load_land(ROOT/'fixtures/vinga-land-expanded-20261017.geojson',margin_m=10,
            review_bounds=(11.55,57.60,11.66,57.67))
        self.assertEqual(len(snapshot.obstacles),24)
        a,b=Vector(500,0),Vector(500,350)
        limited=generate_routes(a,b,snapshot.obstacles,SearchPolicy(clearance_m=5,max_nodes=26,max_candidates=8,max_expansions=1000))
        self.assertEqual(limited.status,'node_limit');self.assertTrue(limited.truncated)
        result=generate_routes(a,b,snapshot.obstacles,SearchPolicy(clearance_m=5,max_nodes=66,max_candidates=8,max_expansions=1000))
        self.assertEqual(result.node_count,60);self.assertEqual(len(result.candidates),8)
        self.assertEqual(result.limit_reason,'max_candidates');self.assertTrue(result.truncated)
        self.assertEqual(result.lengths_m[0],350)
        self.assertEqual(result.candidates[0].waypoints,())
        self.assertEqual(list(result.lengths_m),sorted(result.lengths_m))
        for candidate in result.candidates:
            points=(a,*candidate.waypoints,b)
            self.assertTrue(all(p.speed<900 for p in points))
            for p,q in zip(points,points[1:]):
                self.assertFalse(any(o.intersects(p,q) for o in snapshot.obstacles))

    def test_native_graph_budget_is_offline_only_and_whitelisted(self):
        for v in (0,True,26.0,67,258):
            with self.assertRaisesRegex(ValueError,'nodbudget'):
                calculate_geographic(payload(),weather_config=CONFIG,audit_candidate_limit=2,audit_node_limit=v)
        with self.assertRaisesRegex(ValueError,'nodbudget'):
            calculate_geographic(payload(),weather_config=CONFIG,audit_node_limit=66)
        for field in ('audit_node_limit','weather_config'):
            with self.assertRaises(ValidationError):
                PlanInput(**(payload() | {field:66}))

    def test_real_audit_preserves_qualification_and_entire_segment_controls(self):
        root=ROOT/'artifacts/native-candidate-budget'
        audit=json.loads((root/'audit.json').read_text())
        self.assertFalse(audit['interactive_extension_enabled'])
        self.assertEqual(audit['departure_offsets_seconds'],[0,600,3600,10800])
        for report in audit['reports']:
            self.assertEqual(len(report['alternatives']),report['candidate_limit']*4)
            self.assertEqual(report['geometry_search']['policy']['max_nodes'],66)
            self.assertEqual(report['geometry_search']['policy']['max_expansions'],1000)
            self.assertTrue(report['geometry_search']['truncated'])
            self.assertTrue(report['alternative_comparison']['same_winner'])
        r=json.loads((root/'result.json').read_text())
        self.assertEqual(len(r['alternatives']),32)
        self.assertEqual(len(r['obstacles']['features']),24)
        self.assertEqual(r['weather_provenance']['source_qualification'],'unverified')
        self.assertEqual(r['result_qualification'],'conditional_on_assumptions')
        self.assertTrue(all(v is None for v in r['weather_provenance']['actual_source_issued_at'].values()))
        self.assertEqual(r['planning']['manifest']['parameters']['max_seconds'],1800)
        for route in r['alternatives']:
            self.assertEqual(route['status'],'arrived')
            self.assertEqual(route['weather_segment_status'],'verified')
            self.assertEqual(route['arrival_weather_status'],'passed_at_arrival')
        for product in r['planning']['manifest']['forecast_products']:
            self.assertIn('issued_at',product['assumed_fields'])
        html=(root/'index.html').read_text()
        self.assertIn('Samma alternativ vinner båda kriterierna.',html)
        self.assertIn('17 oktober 2026',html)
        self.assertIn('Geometrisk ordning är inte väderoptimalitet.',html)
