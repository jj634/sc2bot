from sc2.units import Units
from sc2.unit import Unit
from sc2.position import Point2, Point3
from sc2.bot_ai import BotAI
from sc2.ids.ability_id import AbilityId
from sc2.ids.buff_id import BuffId

from typing import Dict, Set, Union

# TODO: figure out relative imports
import sys
sys.path.append(".") # Adds higher directory to python modules path.

from utils.distances import centroid
from routines.terran.medivac_pickup import pickup_micro



class DropTactics:

    # medivacs can travel approx 31.72 during boost,
    # and approx 63.77 between boosts (unupgraded)
    EXPANSION_RADIUS = 15
    BOOST_SAVE_RADIUS = EXPANSION_RADIUS + 64
    BOOST_RADIUS = EXPANSION_RADIUS + 16
    MEDIVAC_LEASH = 2
    

    def __init__(self, marines : Units, medivacs : Units, target : Union[Unit, Point2, Point3], bot_object : BotAI):
        """
        :param marines:
        :param medivacs:
        :param target:
        :param bot_object:
        """
        assert all(not medivac.has_cargo for medivac in medivacs), "medivacs should be empty"
        assert marines.amount == medivacs.amount * 8, "need " + str(medivacs.amount * 8) + " marines for " + str(medivacs.amount) + " medivacs"

        # cannot store unit objects because their distance_calculation_index changes on each iteration
        self._marine_tags : Set[int] = marines.tags
        self._medivac_tags : Set[int] = medivacs.tags
        self._target = target
        self._bot_object = bot_object
        self._mode = 0
        self._loaded = False

    @property
    def marine_tags(self) -> Units:
        """ Returns the tags of marines in this drop. """
        return self._marine_tags

    @property
    def medivac_tags(self) -> Units:
        """ Returns the tags of medivacs in this drop. """
        return self._medivac_tags

    @property
    def mode(self) -> int:
        """
        Returns the status of the drop.
         - 0: Idle
         - 1: Moving towards target
         - 2: Attacking
         - 3: Retreating
        """
        return self._mode

    @property
    def loaded(self) -> bool:
        """ Returns True if the marines are loaded in the medivacs, False otherwise. """
        # TODO: what if all the marines are dead?
        return self._loaded

    async def handle(self, units_by_tag : Dict[int, Unit]):
        alive_medivacs = self._medivac_tags & units_by_tag.keys()
        medivacs : Units = Units({units_by_tag[m_tag] for m_tag in alive_medivacs}, self._bot_object)
        self._medivac_tags = alive_medivacs
        
        loaded_marine_tags : Set[int] = set().union(*(medivac.passengers_tags for medivac in medivacs))
        alive_unloaded_marine_tags = self._marine_tags & units_by_tag.keys()
        unloaded_marines : Units = Units({units_by_tag[m_tag] for m_tag in alive_unloaded_marine_tags}, self._bot_object)
        self._marine_tags = alive_unloaded_marine_tags | loaded_marine_tags

        if self._mode == 0:
            if unloaded_marines: # load up all marines
                medivac_cargos = {
                    medivac : medivac.cargo_left for medivac in medivacs
                }
                for marine in unloaded_marines:
                    free_medivacs = filter(lambda medivac : medivac_cargos[medivac] > 0, medivacs)
                    closest_free_medivac = min((medivac for medivac in free_medivacs), key= lambda u : self._bot_object._distance_squared_unit_to_unit(u, marine))
                    marine.smart(closest_free_medivac)
                    medivac_cargos[closest_free_medivac] -= 1
                for medivac in medivacs:
                    medivac.move(unloaded_marines.random)
            else:
                medivac_centroid : Point2 = centroid(medivacs)
                # move medivacs towards each other if too far apart
                if any(medivac.distance_to(medivac_centroid) > self.MEDIVAC_LEASH for medivac in medivacs):
                    for medivac in medivacs:
                        medivac.move(medivac_centroid)
                else: # move medivacs to target
                    for medivac in medivacs:
                        medivac.move(self._target)
                    self._mode = 1
        elif self._mode == 1:
            # en route to enemy base. constantly boost when possible and outside of BOOST_SAVE_RADIUS
            if all(not medivac.has_cargo for medivac in medivacs):
                self._mode = 2
            else:
                # TODO: just retreat if too many enemy units at target location
                for medivac in medivacs:
                    target_proximity = medivac.distance_to(self._target)
                    if target_proximity <= self.EXPANSION_RADIUS:
                        if (medivac.is_moving):
                            medivac.stop()
                        else:
                            medivac(AbilityId.UNLOADALLAT_MEDIVAC, medivac)
                    elif (
                        not self.BOOST_RADIUS < target_proximity < self.BOOST_SAVE_RADIUS
                        and not medivac.has_buff(BuffId.MEDIVACSPEEDBOOST)
                        and await self._bot_object.can_cast(medivac,AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS)
                    ):
                        medivac(AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS)
        elif self._mode == 2:
            # TODO: retreat if too many enemies
            await pickup_micro(self._bot_object,unloaded_marines, medivacs, self._target)