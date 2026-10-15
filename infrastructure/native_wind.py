"""Frozen source-grid wind samples, deliberately not a routing GridProduct."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class NativeWindSample:
    projection: str
    x_m: tuple[Decimal, ...]
    y_m: tuple[Decimal, ...]
    times: tuple[datetime, ...]
    speed_m_s: tuple  # [time][y][x], preserving source decimal tokens
    direction_from_degrees: tuple
    land_fraction: tuple  # [y][x], never a wind validity mask
    model_reference_time: datetime
    source_hashes: tuple[tuple[str, str], ...]

    @property
    def planning_blockers(self):
        return ('wind_native_geometry_unqualified', 'wind_vector_frame_unqualified',
                'model_issue_time_unverified', 'cross_product_model_run_compatibility_unverified')
