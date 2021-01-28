from sc2.units import Units
from sc2.unit import Unit
from sc2.position import Point2, Point3
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
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
    BOOST_RADIUS = EXPANSION_RADIUS + 16
    BOOST_SAVE_RADIUS = BOOST_RADIUS + 64

    MEDIVAC_LEASH = 2
    

    def __init__(self, marines : Units, medivacs : Units, target : Point2, retreat_point : Point2, bot_object : BotAI, walk : bool = False):
        """
        :param marines:
        :param medivacs:
        :param target:
        :param bot_object:
        :param walk:
        """
        assert all(not medivac.has_cargo for medivac in medivacs), "medivacs should be empty"
        assert marines.amount == medivacs.amount * 8, "need " + str(medivacs.amount * 8) + " marines for " + str(medivacs.amount) + " medivacs"

        # cannot store unit objects because their distance_calculation_index changes on each iteration
        self._marine_tags : Set[int] = marines.tags
        self._medivac_tags : Set[int] = medivacs.tags
        self._target = target
        self._retreat_point = retreat_point
        self._bot_object = bot_object
        self._mode = 2 if walk else 0
        self._walk = walk

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
         - 3: Picking up to retreat
         - 4: Retreating
        """
        return self._mode

    async def handle(self, units_by_tag : Dict[int, Unit]):
        alive_medivac_tags = self._medivac_tags & units_by_tag.keys()
        medivacs : Units = Units({units_by_tag[m_tag] for m_tag in alive_medivac_tags}, self._bot_object)
        self._medivac_tags = alive_medivac_tags
        
        loaded_marines = Units(set().union(*(medivac.passengers for medivac in medivacs)), self._bot_object)
        loaded_marine_tags = loaded_marines.tags
        alive_unloaded_marine_tags = self._marine_tags & units_by_tag.keys()
        unloaded_marines : Units = Units({units_by_tag[m_tag] for m_tag in alive_unloaded_marine_tags}, self._bot_object)
        all_marines : Units = loaded_marines + unloaded_marines
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
        if self._mode == 1:
            # en route to enemy base. constantly boost when possible and outside of BOOST_SAVE_RADIUS
            # TODO: just retreat if too many enemy units at target location
            for medivac in medivacs:
                target_proximity = medivac.distance_to(self._target)
                if target_proximity <= self.EXPANSION_RADIUS:
                    if (medivac.is_moving):
                        medivac.stop()
                    else:
                        self._mode = 2
                elif (
                    not self.BOOST_RADIUS < target_proximity < self.BOOST_SAVE_RADIUS
                    and not medivac.has_buff(BuffId.MEDIVACSPEEDBOOST)
                    and await self._bot_object.can_cast(medivac,AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS)
                ):
                    medivac(AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS)
        if self._mode == 2:
            retreat = False

            if not all_marines:
                retreat = True

            endangered_marines_tags : Set[int] = set()
            enemies_in_marines_range : Set[Unit] = set()

            for marine in unloaded_marines:
                enemies_in_range = self._bot_object.enemy_units.filter(lambda e : e.type_id != UnitTypeId.SCV and e.target_in_range(marine))
                if enemies_in_range:
                    enemies_in_marines_range |= set(enemies_in_range)
                    endangered_marines_tags.add(marine.tag)

            enemy_dps = 0
            for enemy_unit in enemies_in_marines_range:
                enemy_unit_dps = enemy_unit.calculate_dps_vs_target(unloaded_marines.first) if unloaded_marines else enemy_unit.ground_dps
                enemy_dps += enemy_unit_dps
            
            own_dps = all_marines.first.ground_dps * all_marines.amount if all_marines else 0
            print("own_dps: " + str(own_dps) + ", len: " + str(all_marines.amount))
            print("enemy_dps: " + str(enemy_dps) + ", len: " + str(len(enemies_in_marines_range)))
            if enemy_dps > own_dps * 1.5:
                print("too many")
                retreat = True
            
            if retreat:
                self._mode = 3
            else:
                await pickup_micro(
                    bot=self._bot_object,
                    marines=unloaded_marines,
                    medivacs=medivacs,
                    endangered_marines_tags=endangered_marines_tags,
                    target=self._target,
                    retreat_point=self._retreat_point
                )
        if self._mode == 3:
            if unloaded_marines:
                for medivac in medivacs:
                    medivac.move(unloaded_marines.random)
                for marine in unloaded_marines:
                    closest_medivac = medivacs.filter(lambda m : m.cargo_left > 0).sorted(key = lambda m : m.distance_to(marine))
                    marine.smart(closest_medivac.first)
            else:
                self._mode = 4
        if self._mode == 4:
            cargo_medivacs = medivacs.filter(lambda m : m.has_cargo)
            for medivac in medivacs:
                if medivac.distance_to(self._retreat_point) < 5:
                    if not cargo_medivacs:
                        self._mode = 2 if self._walk else 0
                    else:
                        medivac(AbilityId.UNLOADALLAT_MEDIVAC, medivac)
                        if medivac.is_moving:
                            medivac.hold_position()
                else:
                    medivac.move(self._retreat_point)