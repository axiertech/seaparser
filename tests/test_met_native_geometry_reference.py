"""Independent tangent-cone geometry, not an accepted datum or wind transform."""
from math import asin, atan, atan2, cos, degrees, hypot, pi, radians, sin, sqrt, tan
from pathlib import Path
import unittest

from pyproj import CRS, Transformer

from scripts.audit_met_metadata import PROJ4, axis, audit, matrix
from scripts.regional_forecast import load_regional_inputs


FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures/met-nordic-metadata'
RADIUS = 6371000
PARALLEL = radians(63)
CONE = sin(PARALLEL)
# Tangent cone: rho0*n = R*cos(phi0); rho/rho0 = (t0/t)**n.
RHO0 = RADIUS * cos(PARALLEL) / CONE
T0 = tan(pi / 4 + PARALLEL / 2)


def inverse_cone(x, y):
    """Closed form on this northern tangent sphere; no CRS library calls."""
    rho = hypot(x, RHO0 - y)
    theta = atan2(x, RHO0 - y)
    latitude = 2 * atan(T0 * (RHO0 / rho) ** (1 / CONE)) - pi / 2
    return degrees(latitude), 15 + degrees(theta / CONE)


def spherical_distance(a, b):
    lat1, lat2 = radians(a[0]), radians(b[0])
    half_lat, half_lon = radians(b[0] - a[0]) / 2, radians(b[1] - a[1]) / 2
    h = sin(half_lat) ** 2 + cos(lat1) * cos(lat2) * sin(half_lon) ** 2
    return 2 * RADIUS * asin(sqrt(min(1, h)))


def bearing(a, b):
    lat1, lat2, delta_lon = radians(a[0]), radians(b[0]), radians(b[1] - a[1])
    return degrees(atan2(sin(delta_lon) * cos(lat2),
                         cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(delta_lon)))


class METNativeGeometryReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = audit(FIXTURE)  # Hash/byte/projection checks precede reference reads.
        axes = (FIXTURE / 'native-axes.txt').read_text()
        cls.x = axis(axes, 'x', 1796)[692:699]
        cls.y = axis(axes, 'y', 2321)[509:517]
        text = (FIXTURE / 'vinga-latlon.txt').read_text()
        cls.latitude = matrix(text, 'latitude', 8, 7)
        cls.longitude = matrix(text, 'longitude', 8, 7)

    def test_tangent_origin_and_east_west_symmetry(self):
        self.assertAlmostEqual(inverse_cone(0, 0)[0], 63, delta=1e-12)
        self.assertEqual(inverse_cone(0, 0)[1], 15)
        west, east = inverse_cone(-1000, 0), inverse_cone(1000, 0)
        self.assertEqual(west[0], east[0])
        self.assertAlmostEqual(west[1] + east[1], 30, delta=1e-12)
        self.assertLess(west[1], 15)
        self.assertGreater(inverse_cone(0, 1000)[0], 63)

    def test_all_56_nodes_match_provider_and_library_independently(self):
        native = CRS.from_proj4(PROJ4)
        inverse = Transformer.from_crs(native, native.geodetic_crs, always_xy=True)
        distances = []
        for j, y in enumerate(self.y):
            for i, x in enumerate(self.x):
                with self.subTest(row=j, column=i):
                    expected = inverse_cone(float(x), float(y))
                    lon, lat = inverse.transform(float(x), float(y), errcheck=True)
                    # Numerical agreement only, never a routing/datum tolerance.
                    self.assertAlmostEqual(lat, expected[0], delta=1e-10)
                    self.assertAlmostEqual(lon, expected[1], delta=1e-10)
                    provider = float(self.latitude[j][i]), float(self.longitude[j][i])
                    distances.append(spherical_distance(expected, provider))
        self.assertEqual(len(distances), 56)
        self.assertLess(max(distances), .25)  # Existing rounded source angular coordinates.
        self.assertAlmostEqual(max(distances),
            self.report['source_projection_vs_provider_latlon_max_spherical_distance_m'], delta=1e-6)

    def test_native_axis_bearings_are_not_true_east_north(self):
        for y in self.y:
            for x in self.x:
                with self.subTest(x=x, y=y):
                    x, y = float(x), float(y)
                    origin = inverse_cone(x, y)
                    gamma = CONE * (origin[1] - 15)
                    # A 0.1 m chord approximates each local tangent on the source sphere.
                    self.assertAlmostEqual(bearing(origin, inverse_cone(x, y + .1)), gamma, delta=1e-5)
                    self.assertAlmostEqual(bearing(origin, inverse_cone(x + .1, y)), 90 + gamma, delta=1e-5)
                    self.assertLess(gamma, -2.9)
        self.assertEqual(self.report['routing_status'], 'data_unavailable')
        self.assertIsNone(self.report['issued_at'])

    def test_regional_input_uses_exact_axes_covered_by_reference(self):
        wind = load_regional_inputs(FIXTURE.parent).wind
        self.assertEqual(wind.projection, PROJ4)
        self.assertEqual(wind.x_m, self.x)
        self.assertEqual(wind.y_m, self.y)
        for name, digest in self.report['source_hashes'].items():
            self.assertEqual(dict(wind.source_hashes)[name], digest)
        self.assertIn('wind_native_geometry_unqualified', wind.planning_blockers)
        self.assertIn('wind_vector_frame_unqualified', wind.planning_blockers)
