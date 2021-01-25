from sc2.units import Units
from sc2.unit import Unit
from sc2.position import Point2

from typing import Set, Union


def centroid(points : Union[Set[Unit],Set[Point2]]) -> Point2:
    """
    Calculates the centroid for a set of Unit or Point2.

    :param points:
    """
    if isinstance(points, Set[Unit]):
        return sum(unit.position for unit in points) / len(points)
    return sum(point for point in points) / len(points)