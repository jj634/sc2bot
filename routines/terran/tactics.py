from sc2.bot_ai import BotAI
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units

# TODO: figure out relative imports
import sys
sys.path.append(".") # Adds higher directory to python modules path.

from utils.distances import centroid

from typing import Dict, Set


class Tactics:
    MEDIVAC_LEASH = 2

    def __init__(self, marine_tags : Set[int], medivac_tags : Set[int], bot_object : BotAI):
        """
        :param marine_tags:
        :param medivac_tags:
        :param bot_object:
        """
        # assert all(not medivac.has_cargo for medivac in medivacs), "medivacs should be empty"
        assert len(medivac_tags) > 0, "need to have at least 1 medivac"
        assert len(marine_tags) == len(medivac_tags) * 8, f"need {len(medivac_tags) * 8} marines for {len(medivac_tags)} medivacs"

        # cannot store unit objects because their distance_calculation_index changes on each iteration
        self._marine_tags : Set[int] = marine_tags
        self._medivac_tags : Set[int] = medivac_tags
        self._original_medivac_tags = frozenset(medivac_tags)
        self._bot_object : BotAI = bot_object
        self._mode = 0

    def __hash__(self):
        return hash(self._original_medivac_tags)

    def __eq__(self, other):
        try:
            return (self._medivac_tags == other.medivac_tags) and (self._marine_tags == other.marine_tags)
        except:
            return False

    @property
    def marine_tags(self) -> Units:
        """ Returns the tags of marines in this drop. """
        return self._marine_tags

    @marine_tags.setter
    def marine_tags(self, new_marine_tags):
        self._marine_tags = new_marine_tags

    @property
    def medivac_tags(self) -> Units:
        """ Returns the tags of medivacs in this drop. """
        return self._medivac_tags

    @medivac_tags.setter
    def medivac_tags(self, new_medivac_tags):
        self._medivac_tags = new_medivac_tags

    @property
    def position(self, units_by_tag : Dict[int, Unit]) -> Point2:
        """ Returns the centroid of the medivacs in this group. """
        alive_medivac_tags = self._medivac_tags & units_by_tag.keys()
        medivacs : Units = Units({units_by_tag[m_tag] for m_tag in alive_medivac_tags}, self._bot_object)
        self._medivac_tags = alive_medivac_tags

        return centroid(medivacs)

    def perished(self, units_by_tag : Dict[int, Unit]) -> bool:
        """ Returns whether this group has perished (based on living medivacs). """
        alive_medivac_tags = self._medivac_tags & units_by_tag.keys()
        self._medivac_tags = alive_medivac_tags

        return True if len(self._medivac_tags) == 0 else False

    @property
    def mode(self):
        raise NotImplementedError("subclasses must override mode getter")

    async def handle(self, units_by_tag : Dict[int, Unit]):
        raise NotImplementedError("subclasses must override handle")