from datetime import datetime, timezone

from .model import KNOT, Vector
from .environment import Conditions, SyntheticEnvironment
from .calculation import sail_to_target
from .presentation import export_voyage

start = datetime(2026, 1, 1, tzinfo=timezone.utc)
environment = SyntheticEnvironment(lambda position, time: Conditions(Vector(0, 2 * KNOT)))
print(export_voyage(sail_to_target(environment, start, Vector(5 * 1852, 0))))
