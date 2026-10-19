"""Frozen source-grid wind samples, deliberately not a routing GridProduct."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from collections.abc import Sequence
from functools import lru_cache

NATIVE_PROJECTION = '+proj=lcc +lat_0=63 +lon_0=15 +lat_1=63 +lat_2=63 +no_defs +R=6.371e+06'


@lru_cache(maxsize=128)
def _decimal_row_values(tokens):
    return tuple(Decimal(token) for token in tokens.split(','))


@dataclass(frozen=True, eq=False)
class DecimalRow(Sequence):
    """Materialized exact tokens, with bounded Decimal expansion during reads.

    No I/O, rounding or missing-value substitution. Scientific array consumers
    still see the same Decimal sequence; only 128 expanded rows are retained.
    """
    tokens: str
    size: int

    @classmethod
    def from_values(cls,values):
        return cls(','.join(str(v) for v in values),len(values))

    def __len__(self):return self.size
    def __getitem__(self,index):return _decimal_row_values(self.tokens)[index]
    def __iter__(self):return iter(_decimal_row_values(self.tokens))
    def __eq__(self,other):
        if not isinstance(other,Sequence):return NotImplemented
        return tuple(self)==tuple(other)
    __hash__=None


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
