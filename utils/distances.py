from sc2.unit import Unit
from sc2.position import Point2

import operator
from functools import reduce
from typing import List, Tuple, Union

import numpy as np


def centroid(units : List[Unit]) -> Point2:
    """
    Calculates the centroid of a Unit list.

    :param points:
    """
    return reduce(operator.add, (unit.position for unit in units)) / len(units)

def angle(first : Tuple[int, int], second : Tuple[int, int]) -> float:
    """
    Calculates the angle between two 2D vectors in radians.
    The return value will be a float [0, pi], where 0 means they are parallel
    and pi means they are antiparallel.
    
    :param first:
    :param second:
    """

    first_unit_vector = first / np.linalg.norm(first)
    second_unit_vector = second / np.linalg.norm(second)

    return np.arccos(np.dot(first_unit_vector, second_unit_vector))

def perpendicular_clockwise(vector : Tuple[int, int]) -> Tuple[int, int]:
    """
    Returns a unit vector that is clockwise perpendicular to the given vector.

    :param vector:
    """

    unit_vector = vector / np.linalg.norm(vector)
    return (unit_vector[1], -unit_vector[0])

def perpendicular_counterclockwise(vector : Tuple[int, int]) -> Tuple[int, int]:
    """
    Returns a unit vector that is counter-clockwise perpendicular to the given vector.

    :param vector:
    """
    
    unit_vector = vector / np.linalg.norm(vector)
    return (-unit_vector[1], unit_vector[0])