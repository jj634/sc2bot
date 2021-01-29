import sc2

from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId

from sc2 import Race, Difficulty
from sc2.player import Bot, Computer


from typing import Dict, List, Set

# TODO: figure out relative imports
import sys
sys.path.append(".") # Adds higher directory to python modules path.

from routines.terran.drop_tactics import DropTactics
from utils.expansions import get_enemy_expansions

"""
This bot tests medivac pickup micro.
"""


class DropTacticsTest(sc2.BotAI):

    
    # size of harass groups in terms of number of medivacs. scales based on number of bases
    HARASS_SIZE = 1

    def __init__(self):
        self.waiting_army : Units = None
        self.units_by_tag : Dict[int, Unit] = None
        self.enemy_expansions : List[Point2] = None
        self.harass_groups : Set[DropTactics] = set()
        self.harass_assignments : Dict[Point2, DropTactics] = None

    async def on_start(self):
        await self.client.debug_create_unit(
            [
                [UnitTypeId.MEDIVAC, 4, self.start_location.towards(self.game_info.map_center, 15), 1],
                [UnitTypeId.MARINE, 32, self.start_location.towards(self.game_info.map_center, 15), 1],
            ]
        )
        await self.client.debug_control_enemy()
        await self.client.debug_fast_build()
        await self.client.debug_all_resources()

        # TODO: add to this if another expansion encountered, eg a ninja base
        self.enemy_expansions = await get_enemy_expansions(self, limit=8)
        self.harass_assignments = {enemy_expo_p : None for enemy_expo_p in self.enemy_expansions}

    async def on_step(self, iteration):
        self.units_by_tag = {unit.tag : unit for unit in self.all_own_units}

        for expansion_i in range(len(self.enemy_expansions)):
            self._client.debug_text_world(
                text=f"{expansion_i} : {self.enemy_expansions[expansion_i]}",
                pos=self.enemy_expansions[expansion_i],
                color=(0, 255, 0),
                size=12,
            )


        if iteration == 1:
            raxpos : Point2 = await self.find_placement(UnitTypeId.BARRACKS,near=self.start_location.towards(self.game_info.map_center, 5), addon_place = True)
            await self.client.debug_create_unit(
                [
                    [UnitTypeId.BARRACKS, 1, raxpos, 1],
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
                waiting_marines = self.waiting_army(UnitTypeId.MARINE).amount
                waiting_medivacs = self.waiting_army(UnitTypeId.MEDIVAC).amount

                if (
                    waiting_marines >= self.HARASS_SIZE * 8
                    and waiting_medivacs >= self.HARASS_SIZE
                ):
                    new_harass_marines = self.waiting_army(UnitTypeId.MARINE).take(self.HARASS_SIZE * 8)
                    new_harass_medivacs = self.waiting_army(UnitTypeId.MEDIVAC).take(self.HARASS_SIZE)
                    new_harass_group = new_harass_marines + new_harass_medivacs

                    self.waiting_army -= new_harass_group

                    next_targets = list(filter(lambda p : self.harass_assignments[p] is None, self.enemy_expansions))
                    if len(next_targets) > 0:
                        new_drop_tactics = DropTactics(
                            marines=new_harass_marines,
                            medivacs=new_harass_medivacs,
                            target=next_targets[0],
                            retreat_point=self.start_location,
                            bot_object=self,
                            walk=False
                        )

                        self.harass_assignments[next_targets[0]] = new_drop_tactics
                        self.harass_groups.add(new_drop_tactics)


            for group in self.harass_groups:
                await group.handle(self.units_by_tag)

    async def on_unit_created(self, unit: Unit):
        if unit.type_id == UnitTypeId.MARINE or unit.type_id == UnitTypeId.MEDIVAC:
            if self.waiting_army:
                self.waiting_army.append(unit)
            else:
                self.waiting_army = Units([unit], self)

def main():
    sc2.run_game(
        sc2.maps.get("AcropolisLE"),
        [Bot(Race.Terran, DropTacticsTest()), Computer(Race.Terran, Difficulty.VeryEasy)],
        realtime=True,
        disable_fog=True,
    )


if __name__ == "__main__":
    main()