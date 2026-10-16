"""Independent spherical AEQD differential, never a qualified MET wind transform."""
from math import cos, degrees, radians, sin
import unittest

from pyproj import CRS, Transformer


RADIUS = 6371000.0
LATITUDE = 57.633
LONGITUDE = 11.605


class LocalVectorReferenceTests(unittest.TestCase):
    def setUp(self):
        # Synthetic sphere: deliberately no claim of MET sphere / WGS84 binding.
        sphere = CRS.from_proj4(f'+proj=longlat +R={RADIUS}')
        plane = CRS.from_proj4(
            f'+proj=aeqd +lat_0={LATITUDE} +lon_0={LONGITUDE} +R={RADIUS} +units=m')
        self.forward = Transformer.from_crs(sphere, plane, always_xy=True)

    def differential(self, latitude, east, north):
        # Symmetric 1 m tangent chord. Expected derivatives below are analytical.
        dlat = degrees(north / RADIUS)
        dlon = degrees(east / (RADIUS * cos(radians(latitude))))
        a = self.forward.transform(LONGITUDE - dlon, latitude - dlat, errcheck=True)
        b = self.forward.transform(LONGITUDE + dlon, latitude + dlat, errcheck=True)
        return (b[0] - a[0]) / 2, (b[1] - a[1]) / 2

    def test_radial_and_transverse_differentials_have_distinct_scales(self):
        for distance in (0, -1000, 1000, -1000000, 1000000):
            # Distant positions are synthetic stress references, outside routing scope.
            with self.subTest(distance=distance):
                c = distance / RADIUS
                latitude = LATITUDE + degrees(c)
                scale = c / sin(c) if c else 1.0
                for east, north in ((1, 0), (0, 1), (3, -4)):
                    actual = self.differential(latitude, east, north)
                    self.assertAlmostEqual(actual[0], scale * east, delta=2e-8)
                    self.assertAlmostEqual(actual[1], north, delta=2e-8)

    def test_rotation_alone_cannot_represent_distant_transverse_scale(self):
        c = 1000000 / RADIUS
        latitude = LATITUDE + degrees(c)
        east, north = self.differential(latitude, 1, 0)
        self.assertGreater(east, 1.004)
        self.assertAlmostEqual(north, 0, delta=2e-8)
        # Any pure rotation preserves unit length; this differential does not.
        self.assertGreater(east * east + north * north, 1.008)
