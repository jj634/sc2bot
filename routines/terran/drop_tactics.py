from sc2.units import Units
from sc2.unit import Unit
from sc2.position import Point2, Point3
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.ids.buff_id import BuffId

from typing import Dict, List, Set, Union

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
    

    def __init__(self, marine_tags : Units, medivac_tags : Units, targets : List[Point2], retreat_point : Point2, bot_object : BotAI, walk : bool = False):
        """
        :param marine_tags:
        :param medivac_tags:
        :param target:
        :param bot_object:
        :param walk:
        """
        # assert all(not medivac.has_cargo for medivac in medivacs), "medivacs should be empty"
        assert len(medivac_tags) > 0, "need to have at least 1 medivac"
        assert len(marine_tags) == len(medivac_tags) * 8, f"need {len(medivac_tags) * 8} marines for {len(medivac_tags)} medivacs"


        # cannot store unit objects because their distance_calculation_index changes on each iteration
        self._marine_tags : Set[int] = marine_tags
        self._medivac_tags : Set[int] = medivac_tags
        # self._target = target
        self._targets : List[Point2] = targets + [bot_object.enemy_start_locations[0]]
        self._current_target_i : int = 0
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
        """
        Controls the marines and medivacs in this drop, depending on the current mode.

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

        if self._mode == 0:
            # idle
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
                else: # move medivacs to target
                    for medivac in medivacs:
                        medivac.move(self._targets[self._current_target_i])
                    self._mode = 1
        if self._mode == 1:
            # en route to enemy base. constantly boost when possible and outside of BOOST_SAVE_RADIUS
            # TODO: just retreat if too many enemy units at target location
            for medivac in medivacs:
                target_proximity = medivac.distance_to(self._targets[self._current_target_i])
                enemies_in_range = self._bot_object.all_enemy_units.filter(lambda e : medivac.distance_to(e) < 10)
                if target_proximity <= self.BOOST_RADIUS:
                    enemies_in_range_dps = sum(e.calculate_dps_vs_target(medivac) for e in enemies_in_range)
                    if enemies_in_range_dps * 3 > medivac.health:
                        self._mode = 4
                
                if target_proximity <= self.EXPANSION_RADIUS and (await self._bot_object.can_place(UnitTypeId.SENSORTOWER, [medivac.position]))[0]:
                    medivac(AbilityId.UNLOADALLAT_MEDIVAC, medivac)
                    medivac.hold_position()
                    self._mode = 2
                elif (
                    not self.BOOST_RADIUS < target_proximity < self.BOOST_SAVE_RADIUS
                    and not medivac.has_buff(BuffId.MEDIVACSPEEDBOOST)
                    and await self._bot_object.can_cast(medivac,AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS)
                ):
                    medivac(AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS)
                if target_proximity > self.BOOST_RADIUS and enemies_in_range:
                    if not medivac.has_buff(BuffId.MEDIVACSPEEDBOOST) and await self._bot_object.can_cast(medivac,AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS):
                        medivac(AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS)

                    first_enemy = enemies_in_range.first.position
                    enemy_vector = (first_enemy.x - medivac.position.x, first_enemy.y - medivac.position.y)
                    safe_point = (medivac.position.x - enemy_vector[0], medivac.position.y - enemy_vector[1])

                    medivac.move(medivac.position.towards(Point2(safe_point), 3))
                    medivac.move(self._targets[self._current_target_i], queue = True)
        if self._mode == 2:
            # attacking
            # TODO: add "wander" mechanics to find structures at edges of base
            retreat = False

            if not all_marines:
                retreat = True

            endangered_marines_tags : Set[int] = set()
            enemies_in_marines_range : Set[Unit] = set()

            for marine in unloaded_marines:
                enemies_in_range = self._bot_object.enemy_units.filter(lambda e : e.type_id != UnitTypeId.SCV and e.target_in_range(marine, bonus_distance = 2))
                if enemies_in_range:
                    enemies_in_marines_range |= set(enemies_in_range)
                    endangered_marines_tags.add(marine.tag)

            enemy_dps = 0
            for enemy_unit in enemies_in_marines_range:
                enemy_unit_dps = enemy_unit.calculate_dps_vs_target(unloaded_marines.first) if unloaded_marines else enemy_unit.ground_dps
                enemy_dps += enemy_unit_dps
            
            own_dps = all_marines.first.ground_dps * all_marines.amount if all_marines else 0
            # print("own_dps: " + str(own_dps) + ", len: " + str(all_marines.amount))
            # print("enemy_dps: " + str(enemy_dps) + ", len: " + str(len(enemies_in_marines_range)))
            if enemy_dps > own_dps * 1.5:
                # print("too many")
                retreat = True
            
            enemy_units_in_expo = self._bot_object.all_enemy_units.filter(lambda u : self._targets[self._current_target_i].distance_to(u) <= self.EXPANSION_RADIUS)
            deployed_marines = unloaded_marines.filter(lambda m : self._targets[self._current_target_i].distance_to(m) <= 10)
            if not enemy_units_in_expo and deployed_marines.amount == len(self._marine_tags):
                # no more units / structures remaining at this location;
                # move on to next target
                self._current_target_i = min(self._current_target_i + 1, len(self._targets) - 1)

            if retreat:
                self._mode = 3
            else:
                await pickup_micro(
                    bot=self._bot_object,
                    marines=unloaded_marines,
                    medivacs=medivacs,
                    endangered_marines_tags=endangered_marines_tags,
                    target=self._targets[self._current_target_i],
                    retreat_point=self._retreat_point
                )
        if self._mode == 3:
            # picking up to retreat
            if unloaded_marines:
                for medivac in medivacs:
                    medivac.move(unloaded_marines.random)
                for marine in unloaded_marines:
                    closest_medivac = medivacs.filter(lambda m : m.cargo_left > 0).sorted(key = lambda m : m.distance_to(marine))
                    if closest_medivac:
                        marine.smart(closest_medivac.first)
            else:
                self._mode = 4
        if self._mode == 4:
            # retreating
            cargo_medivacs = medivacs.filter(lambda m : m.has_cargo)
            for medivac in medivacs:
                if medivac.distance_to(self._retreat_point) < 5:
                    if not cargo_medivacs:
                        self._current_target_i = 0
                        self._mode = 2 if self._walk else 0
                    else:
                        medivac(AbilityId.UNLOADALLAT_MEDIVAC, medivac)
                        if medivac.is_moving:
                            medivac.hold_position()
                else:
                    if not medivac.has_buff(BuffId.MEDIVACSPEEDBOOST) and await self._bot_object.can_cast(medivac,AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS):
                        medivac(AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS)
                    
                    enemies_in_range = self._bot_object.all_enemy_units.filter(lambda e : e.target_in_range(medivac, bonus_distance = 3))
                    if enemies_in_range:
                        first_enemy = enemies_in_range.first.position
                        enemy_vector = (first_enemy.x - medivac.position.x, first_enemy.y - medivac.position.y)
                        safe_point = (medivac.position.x - enemy_vector[0], medivac.position.y - enemy_vector[1])

                        medivac.move(medivac.position.towards(Point2(safe_point), 3))
                        medivac.move(self._retreat_point, queue = True)
                    else:
                        medivac.move(self._retreat_point)