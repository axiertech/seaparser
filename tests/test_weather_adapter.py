"""Unit tests for the provider-agnostic weather adapter."""
import unittest
from datetime import datetime, timedelta, timezone

from infrastructure.weather_adapter import StubProvider, WeatherSnapshot, is_usable


class IsUsableTests(unittest.TestCase):
    """Tests for the is_usable freshness and trust checks."""

    def setUp(self):
        """Set a fixed timezone-aware reference time."""
        self.now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    def test_missing_snapshot_is_unusable(self):
        """A missing snapshot is never usable."""
        self.assertFalse(is_usable(None, self.now))

    def test_estimated_snapshot_is_unusable_even_when_fresh(self):
        """Estimated data is rejected even with a fresh timestamp."""
        snapshot = WeatherSnapshot(as_of=self.now, estimated=True)
        self.assertFalse(is_usable(snapshot, self.now))

    def test_missing_as_of_is_unusable(self):
        """A snapshot without a timestamp is unusable."""
        snapshot = WeatherSnapshot(as_of=None, estimated=False)
        self.assertFalse(is_usable(snapshot, self.now))

    def test_unparseable_as_of_is_unusable(self):
        """A non-datetime as_of value is unusable."""
        snapshot = WeatherSnapshot(as_of="not-a-datetime", estimated=False)
        self.assertFalse(is_usable(snapshot, self.now))

    def test_stale_snapshot_is_unusable(self):
        """A snapshot older than max_age_s is unusable."""
        old = self.now - timedelta(seconds=6 * 3600 + 1)
        snapshot = WeatherSnapshot(as_of=old, estimated=False)
        self.assertFalse(is_usable(snapshot, self.now))

    def test_future_snapshot_is_unusable(self):
        """A snapshot with a future timestamp is unusable."""
        future = self.now + timedelta(seconds=1)
        snapshot = WeatherSnapshot(as_of=future, estimated=False)
        self.assertFalse(is_usable(snapshot, self.now))

    def test_fresh_non_estimated_snapshot_is_usable(self):
        """A fresh, non-estimated snapshot is usable."""
        fresh = self.now - timedelta(seconds=60)
        snapshot = WeatherSnapshot(as_of=fresh, estimated=False)
        self.assertTrue(is_usable(snapshot, self.now))

    def test_exact_max_age_is_usable(self):
        """A snapshot exactly at max_age_s is still usable."""
        at_limit = self.now - timedelta(seconds=6 * 3600)
        snapshot = WeatherSnapshot(as_of=at_limit, estimated=False)
        self.assertTrue(is_usable(snapshot, self.now))

    def test_naive_as_of_is_unusable(self):
        """A naive (timezone-less) as_of is rejected as unknown."""
        naive = datetime(2026, 1, 1, 11, 59, 0)
        snapshot = WeatherSnapshot(as_of=naive, estimated=False)
        self.assertFalse(is_usable(snapshot, self.now))


class StubProviderTests(unittest.TestCase):
    """Tests for the StubProvider."""

    def test_fetch_returns_estimated_snapshot_with_current_utc_time(self):
        """Fetch returns an estimated snapshot stamped with current UTC time."""
        provider = StubProvider()
        snapshot = provider.fetch(58.0, 11.0)
        self.assertIsInstance(snapshot, WeatherSnapshot)
        self.assertTrue(snapshot.estimated)
        self.assertIsNotNone(snapshot.as_of)
        self.assertEqual(snapshot.as_of.tzinfo, timezone.utc)
        self.assertIsNone(snapshot.wind_speed_ms)
        self.assertIsNone(snapshot.wave_height_m)
        self.assertIsNone(snapshot.current_speed_ms)


if __name__ == "__main__":
    unittest.main()
