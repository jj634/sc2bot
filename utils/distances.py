from sc2.units import Units
from sc2.unit import Unit
from sc2.position import Point2

import operator
from functools import reduce
from typing import List, Union


def centroid(units : List[Unit]) -> Point2:
    """
    Calculates the centroid for a set of Unit or Point2.

    :param points:
    """
    return reduce(operator.add, (unit.position for unit in units)) / len(units)