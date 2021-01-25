from sc2.units import Units
from sc2.unit import Unit
from sc2.position import Point2, Point3
from sc2.bot_ai import BotAI
from sc2.ids.ability_id import AbilityId
from sc2.ids.buff_id import BuffId

from typing import Union

# TODO: figure out relative imports
import sys
sys.path.append(".") # Adds higher directory to python modules path.

from utils.distances import centroid
from routines.terran.medivac_pickup import pickup_micro



class DropTactics:

    BOOST_SAVE_RADIUS = 50
    BOOST_RADIUS = 25
    EXPANSION_RADIUS = 15
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

        self._marines = marines
        self._medivacs = medivacs
        self._target = target
        self._bot_object = bot_object
        self._mode = 0
        self._loaded = False

    @property
    def marines(self) -> Units:
        """ Returns the marines in this drop. """
        return self._marines

    @property
    def medivacs(self) -> Units:
        """ Returns the medivacs in this drop. """
        return self._medivacs

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

    async def handle(self):
        if self._mode == 0:
            unloaded_marines = self._marines.filter(lambda m : all(m not in medivac.passengers for medivac in self._medivacs))
            if unloaded_marines: # load up all marines
                medivac_cargos = {
                    medivac : medivac.cargo_left for medivac in self._medivacs
                }
                for marine in unloaded_marines:
                    free_medivacs = filter(lambda medivac : medivac_cargos[medivac] > 0, self._medivacs)
                    closest_free_medivac = min((medivac for medivac in free_medivacs), key= lambda u : u.distance_to(marine))
                    marine.smart(closest_free_medivac)
                    medivac_cargos[closest_free_medivac] -= 1
                for medivac in self._medivacs:
                    medivac.move(unloaded_marines.random)
            else:
                medivac_centroid : Point2 = centroid(self._medivacs)
                # move medivacs towards each other if too far apart
                if any(medivac.distance_to(medivac_centroid) > self.MEDIVAC_LEASH for medivac in self._medivacs):
                    for medivac in self._medivacs:
                        medivac.move(medivac_centroid)
                else: # move medivacs to target
                    for medivac in self._medivacs:
                        medivac.move(self._target)
                    self._mode = 1
        elif self._mode == 1:
            # en route to enemy base. constantly boost when possible and outside of BOOST_SAVE_RADIUS
            if all(not medivac.has_cargo for medivac in self._medivacs):
                self._mode = 2
            else:
                # TODO: just retreat if too many enemy units at target location
                for medivac in self._medivacs:
                    target_proximity = medivac.distance_to(self._target)
                    if target_proximity <= self.EXPANSION_RADIUS:
                        medivac(AbilityId.UNLOADALLAT_MEDIVAC, medivac)
                    elif (
                        not self.BOOST_RADIUS < target_proximity < self.BOOST_SAVE_RADIUS
                        and not medivac.has_buff(BuffId.MEDIVACSPEEDBOOST)
                        and await self._bot_object.can_cast(medivac,AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS)
                    ):
                        medivac(AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS)
        elif self._mode == 2:
            # TODO: retreat if too many enemies
            await pickup_micro(self._bot_object,self._marines, self._medivacs, self._target)