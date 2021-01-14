import sc2
from sc2.position import Point2, Point3
from sc2 import Race, Difficulty
from sc2.data import Result
from sc2.player import Bot, Computer
from sc2.unit import Unit
from sc2.units import Units
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.ids.ability_id import AbilityId
from sc2.ids.buff_id import BuffId

# TODO: figure out relative imports
import sys
sys.path.append(".") # Adds higher directory to python modules path.

from base_bots.stimpack import StimBot

"""
This bot tests medivac pickup micro.
"""


class MedivacPickup(sc2.BotAI):
    async def on_start(self):
        await self.client.debug_create_unit(
            [
                [UnitTypeId.MEDIVAC, 2, self.start_location.towards(self.game_info.map_center, 40), 1],
                [UnitTypeId.MARINE, 16, self.start_location.towards(self.game_info.map_center, 40), 1],
                [UnitTypeId.MEDIVAC, 2, self.game_info.map_center, 2],
                [UnitTypeId.MARINE, 16, self.game_info.map_center, 2],
            ]
        )
        await self.client.debug_control_enemy()
        await self.client.debug_fast_build()
        await self.client.debug_all_resources()

    async def on_step(self, iteration):
        if iteration == 1:
            raxpos_1 : Point2 = await self.find_placement(UnitTypeId.BARRACKS,near=self.start_location.towards(self.game_info.map_center, 5), addon_place = True)
            raxpos_2 : Point2 = await self.find_placement(UnitTypeId.BARRACKS,near=self.enemy_start_locations[0].towards(self.game_info.map_center, 5), addon_place = True)
            await self.client.debug_create_unit(
                [
                    [UnitTypeId.BARRACKS, 1, raxpos_1, 1],
                    [UnitTypeId.BARRACKS, 1, raxpos_2, 2],
                ]
            )

        if iteration > 1:
            depot = self.structures(UnitTypeId.SUPPLYDEPOT)
            barracks = self.structures(UnitTypeId.BARRACKS)
            if not barracks and not depot and self.already_pending(UnitTypeId.SUPPLYDEPOT) == 0:
                await self.build(UnitTypeId.SUPPLYDEPOT, near = self.start_location.towards(self.game_info.map_center, 5))
            if depot and self.already_pending(UnitTypeId.BARRACKS) == 0 and not barracks:
                pos : Point2 = await self.find_placement(UnitTypeId.BARRACKS,near=self.start_location.towards(self.game_info.map_center, 5), addon_place = True)
                await self.build(UnitTypeId.BARRACKS, near=pos)

            for barrack in barracks.ready.filter(lambda b : not b.has_add_on):
                barrack.build(UnitTypeId.BARRACKSTECHLAB)

            techlab_rax = barracks.ready.filter(lambda b : b.has_techlab).random_or(None)
            if techlab_rax and self.already_pending_upgrade(UpgradeId.STIMPACK) == 0:
                techlab = self.structures.find_by_tag(tag = techlab_rax.add_on_tag)
                techlab.research(UpgradeId.STIMPACK)

            if self.already_pending_upgrade(UpgradeId.STIMPACK) > 0:
                await self.attack()

    async def attack(self):
        """
        Send marines to attack once there are 16 marines and 2 medivacs.
         - Marines a move to enemy main
         - Medivacs follow marines
         - Stim when in range of an enemy unit
         - When a marine falls below 20 hp, pick it up and drop it immediately ?
         - When a marine falls below 10 hp, pick it up and keep it
        """
        # MEDIVAC_RANGE = 5
        MARINE_BOOST_THRESHOLD = 30
        MARINE_PICKUP_THRESHOLD = 15

        marines = self.units(UnitTypeId.MARINE)
        medivacs = self.units(UnitTypeId.MEDIVAC)

        endangered_marines_tags = set()

        for marine in marines:
            enemies_in_range = self.enemy_units.filter(lambda e : e.target_in_range(marine))
            if enemies_in_range:
                endangered_marines_tags.add(marine.tag)
            if marines.amount >= 16 and medivacs.amount >= 2:
                marine.attack(self.enemy_start_locations[0])
            if enemies_in_range and not marine.has_buff(BuffId.STIMPACK):
                marine(AbilityId.EFFECT_STIM_MARINE)

        sorted_marines = marines.sorted(key = lambda m : m.health)
        sorted_marines_iter = iter(sorted_marines)

        endangered_marines = sorted_marines.filter(lambda m : m.tag in endangered_marines_tags)
        endangered_marines_iter = iter(endangered_marines)
            
        for medivac in medivacs:
            if medivac.has_cargo:
                # drop off at closest safe position
                medivac_endangered = self.enemy_units.filter(lambda e : e.type_id != UnitTypeId.SCV and e.target_in_range(medivac))
                if medivac_endangered:
                    medivac.move(self.start_location)
                else:
                    medivac(AbilityId.UNLOADALLAT_MEDIVAC, medivac)
            elif not (len(medivac.orders) > 0 and medivac.orders[0].ability.id == AbilityId.LOAD_MEDIVAC):
                next_endangered_marine = next(endangered_marines_iter, None)
                if next_endangered_marine:
                    if next_endangered_marine.health <= MARINE_BOOST_THRESHOLD and next_endangered_marine.health > MARINE_PICKUP_THRESHOLD:
                        if medivac.has_buff(BuffId.MEDIVACSPEEDBOOST) or not self.can_cast(medivac,AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS):
                            medivac(AbilityId.MEDIVACHEAL_HEAL, next_endangered_marine)
                        else:
                            medivac(AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS)
                    elif next_endangered_marine.health <= MARINE_PICKUP_THRESHOLD:
                        # move and load
                        medivac(AbilityId.LOAD_MEDIVAC,next_endangered_marine)
                elif marines:
                    next_marine = next(sorted_marines_iter, sorted_marines.random_or(None))
                    if next_marine:
                        medivac.attack(next_marine.position)
                else:
                    # no marines
                    medivac.move(self.start_location)


def main():
    sc2.run_game(
        sc2.maps.get("AcropolisLE"),
        [Bot(Race.Terran, MedivacPickup()), Bot(Race.Terran, StimBot())],
        realtime=True,
        disable_fog=True,
    )


if __name__ == "__main__":
    main()