"""Syntetiska slutna hinder i lokalt öst/nord-plan, inga externa data."""
from dataclasses import dataclass
from math import isfinite

from .model import Vector


class ObstacleCollision(ValueError):
    """Ett startläge eller helt integrerat färdsegment träffar ett hinder."""


@dataclass(frozen=True)
class Rectangle:
    name: str
    min_east: float
    min_north: float
    max_east: float
    max_north: float
    margin_m: float = 0

    def __post_init__(self):
        if (not self.name or not all(isfinite(v) for v in
                (self.min_east, self.min_north, self.max_east, self.max_north, self.margin_m))
                or self.min_east >= self.max_east or self.min_north >= self.max_north
                or self.margin_m < 0):
            raise ValueError("Ogiltigt syntetiskt rektangelhinder")

    def intersects(self, start: Vector, end: Vector) -> bool:
        """Slab-klippning av hela slutna segmentet; kantkontakt är kollision."""
        if not all(isfinite(v) for v in (start.east, start.north, end.east, end.north)):
            raise ValueError("Segmentpositioner måste vara finita")
        enter, leave = 0.0, 1.0
        for origin, destination, low, high in (
            (start.east, end.east, self.min_east - self.margin_m, self.max_east + self.margin_m),
            (start.north, end.north, self.min_north - self.margin_m, self.max_north + self.margin_m),
        ):
            delta = destination - origin
            if delta == 0:
                if origin < low or origin > high:
                    return False
                continue
            a, b = (low - origin) / delta, (high - origin) / delta
            enter, leave = max(enter, min(a, b)), min(leave, max(a, b))
            if enter > leave:
                return False
        return True


def check_segment(start, end, obstacles):
    for obstacle in obstacles:
        if obstacle.intersects(start, end):
            raise ObstacleCollision(f"Färdsegmentet träffar syntetiskt hinder: {obstacle.name}")
