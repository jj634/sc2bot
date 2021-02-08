from __future__ import annotations


from sc2.unit import Unit
from sc2.units import Units
from sc2.position import Point2
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.ids.buff_id import BuffId

from .tactics import Tactics
from .drop_tactics import DropTactics

# TODO: figure out relative imports
import sys
sys.path.append(".") # Adds higher directory to python modules path.

from utils.distances import centroid

from typing import Dict, Set, Union


class JoinTactics(Tactics):
    """
    Class for a group of medivacs joining up with a target DropTactics or another JoinTactics.
    """

    def __init__(self, marine_tags : Set[int], medivac_tags : Set[int], bot_object : BotAI, assignment : Union[DropTactics, JoinTactics]):
        """
        :param marine_tags:
        :param medivac_tags:
        :param bot_object:
        :param assignment:
        """
        super().__init__(marine_tags, medivac_tags, bot_object)

        assert type(assignment) in [DropTactics, JoinTactics], "assignment must be either a DropTactics or JoinTactics object"
        self._assignment : Union[DropTactics, JoinTactics] = assignment

    @property
    def mode(self):
        """
        Returns the current mode of this JoinTactics object.
         - 0: Unloaded, fresh from waiting army
         - 1: Loaded and en route to assignment
        """
        return self._mode

    @property
    def assignment(self) -> Union[DropTactics, JoinTactics]:
        """ Returns the current assignment. """
        return self._assignment

    @assignment.setter
    def assignment(self, new_assignment):
        if type(new_assignment) in [DropTactics, JoinTactics] and not new_assignment.perished:
            self._assignment = new_assignment
        else:
            return Exception("Need a valid new assignment")

    async def handle(self, units_by_tag : Dict[int, Unit]):
        """
        Controls the medivacs in this group depending on the current mode.
        Returns True if near assignment, else False.

        :param units_by_tag:
        """

        alive_medivac_tags = self._medivac_tags & units_by_tag.keys()
        medivacs : Units = Units({units_by_tag[m_tag] for m_tag in alive_medivac_tags}, self._bot_object)
        self._medivac_tags = alive_medivac_tags

        loaded_marines = Units(set().union(*(medivac.passengers for medivac in medivacs)), self._bot_object)
        loaded_marine_tags = loaded_marines.tags
        alive_unloaded_marine_tags = self._marine_tags & units_by_tag.keys()
        unloaded_marines : Units = Units({units_by_tag[m_tag] for m_tag in alive_unloaded_marine_tags}, self._bot_object)
        all_marines : Units = loaded_marines + unloaded_marines
        self._marine_tags = alive_unloaded_marine_tags | loaded_marine_tags

        assignment_pos = self._assignment.position(units_by_tag)

        if self._mode == 0:
            if unloaded_marines: # load up all marines
                for marine in unloaded_marines:
                    closest_medivac = medivacs.filter(lambda m : m.cargo_left > 0).sorted(key = lambda m : m.distance_to(marine))
                    if closest_medivac:
                        marine.smart(closest_medivac.first)
                for medivac in medivacs:
                    medivac.move(unloaded_marines.random)
            else:
                medivac_centroid : Point2 = centroid(medivacs)
                # move medivacs towards each other if too far apart
                if any(medivac.distance_to(medivac_centroid) > self.MEDIVAC_LEASH for medivac in medivacs):
                    for medivac in medivacs:
                        medivac.move(medivac_centroid)
                else: # move medivacs to assignment
                    for medivac in medivacs:
                        medivac.move(assignment_pos)
                    self._mode = 1
        elif self._mode == 1:
            for medivac in medivacs:
                target_proximity = medivac.distance_to(assignment_pos)
                enemies_in_range = self._bot_object.all_enemy_units.filter(lambda e : medivac.distance_to(e) < 10)

                if target_proximity <= self.MEDIVAC_LEASH:
                    return True
                else:
                    if (
                        not medivac.has_buff(BuffId.MEDIVACSPEEDBOOST)
                        and await self._bot_object.can_cast(medivac,AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS)
                    ):
                        medivac(AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS)
                    if enemies_in_range:
                        first_enemy = enemies_in_range.first.position
                        enemy_vector = (first_enemy.x - medivac.position.x, first_enemy.y - medivac.position.y)
                        safe_point = (medivac.position.x - enemy_vector[0], medivac.position.y - enemy_vector[1])

                        medivac.move(medivac.position.towards(Point2(safe_point), 3))
                        medivac.move(assignment_pos, queue = True)
                    else:
                        medivac.move(assignment_pos)

        return False